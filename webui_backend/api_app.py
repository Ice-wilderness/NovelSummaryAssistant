from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from logic.llm_api import fetch_available_models

from .config_models import (
    ApiConfig,
    ArticleWordCounts,
    ArticleSummaryRequest,
    CustomSummaryRequest,
    NovelSummaryRequest,
    NovelWordCounts,
    SplitterRequest,
)
from .config_service import (
    delete_prompt_module,
    load_api_configs,
    load_prompt_templates,
    load_user_settings,
    load_workflow_prompt_config,
    prepare_api_configs_for_save,
    prepare_user_settings_for_save,
    public_api_configs,
    reset_prompt_template,
    reset_workflow_prompt_node,
    resolve_api_config,
    save_api_configs,
    save_prompt_template,
    save_user_settings,
    update_workflow_prompt_node,
    upsert_prompt_module,
)
from .file_services import ensure_prompt_cache_dir, get_project_root, get_runtime_base_path
from .local_picker import pick_directory
from .project_workspace import ProjectWorkspaceService, UploadedFileRef
from .task_runtime import TaskRuntime, TaskType
from .workflow_services import (
    create_article_summary_runner,
    create_custom_summary_runner,
    create_novel_summary_runner,
    create_splitter_runner,
    find_api_config,
    select_api_configs,
)


def _default_api_config_path() -> Path:
    return get_project_root() / "api_configs.json"


def _default_frontend_dist_dir() -> Path:
    return get_project_root() / "frontend" / "dist"


def _default_user_settings_path(runtime_base_path: Path) -> Path:
    return runtime_base_path / "user_settings.json"


def _record_response(record) -> Dict[str, Any]:
    return record.to_dict()


def _task_result_status(result_summary: str | None) -> str:
    normalized = str(result_summary or "").strip().lower()
    if normalized == "failed" or normalized.startswith("error:"):
        return "failed"
    return "success"


def _get_prompt_template(cache_dir: Path, prompt_key: str):
    for template in load_prompt_templates(str(cache_dir)):
        if template.key == prompt_key:
            return template
    raise HTTPException(status_code=404, detail=f"Unknown prompt key: {prompt_key}")


def _browse_title(payload: Dict[str, Any] | None, default_title: str) -> str:
    if not payload:
        return default_title
    title = str(payload.get("title", "")).strip()
    return title or default_title


def _normalize_user_path_value(path_value: str) -> tuple[Path, bool]:
    from urllib.parse import unquote, urlparse

    path_str = path_value.strip()
    came_from_file_uri = path_str.lower().startswith("file://")
    if path_str.lower().startswith("file://"):
        try:
            parsed = urlparse(path_str)
            if parsed.netloc and parsed.netloc.lower() != "localhost":
                path_str = f"//{parsed.netloc}{unquote(parsed.path)}"
            elif parsed.path:
                path_str = unquote(parsed.path)
            if path_str.startswith("/") and len(path_str) > 2 and path_str[2] == ":":
                path_str = path_str[1:]
        except ValueError:
            path_str = path_str.replace("file:///", "").replace("file://", "")

    path = Path(path_str).expanduser()
    is_absolute = path.is_absolute()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve(strict=False), is_absolute or came_from_file_uri


def _payload_file_ids(payload: Dict[str, Any]) -> List[str]:
    raw_ids = payload.get("uploaded_file_ids") or payload.get("upload_ids") or []
    if isinstance(raw_ids, list):
        return [str(item) for item in raw_ids if str(item).strip()]
    return []


def _payload_project_slug(payload: Dict[str, Any]) -> str:
    return str(payload.get("project_slug", "")).strip()


def _payload_project_name(payload: Dict[str, Any]) -> str:
    return str(payload.get("project_name", "")).strip()


def _payload_custom_output(payload: Dict[str, Any]) -> str:
    return str(
        payload.get("custom_output_directory_path")
        or payload.get("custom_output_directory")
        or ""
    ).strip()


def create_app(
    *,
    api_config_path: str | Path | None = None,
    prompt_cache_dir: str | Path | None = None,
    frontend_dist_dir: str | Path | None = None,
    runtime_base_path: str | Path | None = None,
    user_settings_path: str | Path | None = None,
    runtime: TaskRuntime | None = None,
) -> FastAPI:
    app = FastAPI(title="NovelSummaryAssistant WebUI API")
    app.state.runtime = runtime or TaskRuntime()
    app.state.api_config_path = Path(api_config_path) if api_config_path else _default_api_config_path()
    app.state.prompt_cache_dir = (
        Path(prompt_cache_dir) if prompt_cache_dir else ensure_prompt_cache_dir()
    )
    app.state.frontend_dist_dir = (
        Path(frontend_dist_dir) if frontend_dist_dir else _default_frontend_dist_dir()
    )
    app.state.runtime_base_path = (
        Path(runtime_base_path) if runtime_base_path else get_runtime_base_path()
    )
    app.state.user_settings_path = (
        Path(user_settings_path)
        if user_settings_path
        else _default_user_settings_path(app.state.runtime_base_path)
    )

    def project_service() -> ProjectWorkspaceService:
        settings = load_user_settings(str(app.state.user_settings_path))
        return ProjectWorkspaceService(
            app.state.runtime_base_path,
            default_export_directory=settings.default_export_directory,
        )

    def project_to_response(metadata):
        service = project_service()
        metadata.default_output_directory = str(
            service.default_export_dir(metadata.project_slug, metadata.workflow_type)
        )
        if metadata.latest_task_id:
            task = app.state.runtime.get_task(str(metadata.latest_task_id))
            if task:
                metadata.latest_task_status = task.status.value
        metadata.progress = service.scan_project_progress(metadata)
        data = metadata.to_dict()
        return data

    def resolve_project_uploads(
        payload: Dict[str, Any],
        workflow_type: TaskType,
    ) -> tuple[str, str, str, Path, List[UploadedFileRef]]:
        upload_ids = _payload_file_ids(payload)
        project_slug = _payload_project_slug(payload)
        if not upload_ids:
            raise ValueError("uploaded_file_ids is required")
        if not project_slug:
            raise ValueError("project_slug is required when uploaded_file_ids is provided")
        requested_output_directory = _payload_custom_output(payload)
        service = project_service()
        uploads = service.resolve_upload_refs(project_slug, upload_ids)
        output_dir, custom_output_directory = service.resolve_output_selection(
            project_slug=project_slug,
            workflow_type=workflow_type.value,
            custom_output_directory=requested_output_directory,
            create=True,
        )
        return (
            project_slug,
            _payload_project_name(payload),
            custom_output_directory,
            output_dir,
            uploads,
        )

    def add_project_fields(request, payload: Dict[str, Any], output_dir: Path | None = None):
        request.project_name = _payload_project_name(payload)
        request.project_slug = _payload_project_slug(payload)
        request.uploaded_file_ids = _payload_file_ids(payload)
        request.custom_output_directory_path = _payload_custom_output(payload)
        if output_dir is not None:
            request.managed_output_directory_path = str(output_dir)

    def wrap_runner_with_project_status(runner, request):
        if not getattr(request, "project_slug", ""):
            return runner

        async def wrapped(record, pause_signal, emit):
            try:
                result = await runner(record, pause_signal, emit)
                project_service().update_project_output(
                    request.project_slug,
                    project_name=getattr(request, "project_name", ""),
                    custom_output_directory=getattr(request, "custom_output_directory_path", ""),
                    latest_task_id=record.task_id,
                    latest_task_status=_task_result_status(result),
                )
                return result
            except asyncio.CancelledError:
                project_service().update_project_output(
                    request.project_slug,
                    project_name=getattr(request, "project_name", ""),
                    custom_output_directory=getattr(request, "custom_output_directory_path", ""),
                    latest_task_id=record.task_id,
                    latest_task_status="cancelled",
                )
                raise
            except Exception:
                project_service().update_project_output(
                    request.project_slug,
                    project_name=getattr(request, "project_name", ""),
                    custom_output_directory=getattr(request, "custom_output_directory_path", ""),
                    latest_task_id=record.task_id,
                    latest_task_status="failed",
                )
                raise

        return wrapped

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/config/api")
    async def get_api_config():
        configs = load_api_configs(str(app.state.api_config_path))
        return {"items": public_api_configs(configs)}

    @app.post("/api/config/api")
    async def save_api_config(payload: List[Dict[str, Any]]):
        existing_configs = load_api_configs(str(app.state.api_config_path))
        try:
            configs = prepare_api_configs_for_save(payload, existing_configs)
            save_api_configs(str(app.state.api_config_path), configs)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"items": public_api_configs(configs)}

    @app.get("/api/settings")
    async def get_user_settings():
        return load_user_settings(str(app.state.user_settings_path)).to_dict()

    @app.post("/api/settings")
    async def update_user_settings(payload: Dict[str, Any]):
        try:
            settings = prepare_user_settings_for_save(payload)
            save_user_settings(str(app.state.user_settings_path), settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return settings.to_dict()

    @app.delete("/api/settings/default-export-directory")
    async def clear_default_export_directory():
        settings = load_user_settings(str(app.state.user_settings_path))
        settings.default_export_directory = ""
        save_user_settings(str(app.state.user_settings_path), settings)
        return settings.to_dict()

    @app.get("/api/prompts")
    async def get_prompts():
        templates = load_prompt_templates(str(app.state.prompt_cache_dir))
        workflow_config = load_workflow_prompt_config(str(app.state.prompt_cache_dir))
        return {
            "items": [template.to_dict() for template in templates],
            "workflow_config": workflow_config.to_dict(),
        }

    @app.post("/api/prompts/modules")
    async def save_prompt_module(payload: Dict[str, Any]):
        try:
            config = upsert_prompt_module(str(app.state.prompt_cache_dir), payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return config.to_dict()

    @app.delete("/api/prompts/modules/{module_id}")
    async def remove_prompt_module(module_id: str):
        try:
            config = delete_prompt_module(str(app.state.prompt_cache_dir), module_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return config.to_dict()

    @app.post("/api/prompts/{prompt_key}")
    async def save_prompt(prompt_key: str, payload: Dict[str, Any]):
        template = _get_prompt_template(app.state.prompt_cache_dir, prompt_key)
        template.text = str(payload.get("text", ""))
        save_prompt_template(str(app.state.prompt_cache_dir), template)
        return template.to_dict()

    @app.post("/api/prompts/{prompt_key}/reset")
    async def reset_prompt(prompt_key: str):
        template = _get_prompt_template(app.state.prompt_cache_dir, prompt_key)
        reset_prompt_template(str(app.state.prompt_cache_dir), template)
        template.text = template.default_text
        return template.to_dict()

    @app.post("/api/prompts/nodes/{prompt_key}")
    async def save_prompt_node(prompt_key: str, payload: Dict[str, Any]):
        try:
            node = update_workflow_prompt_node(
                str(app.state.prompt_cache_dir),
                prompt_key,
                payload,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return node.to_dict()

    @app.post("/api/prompts/nodes/{prompt_key}/reset")
    async def reset_prompt_node(prompt_key: str):
        try:
            node = reset_workflow_prompt_node(str(app.state.prompt_cache_dir), prompt_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return node.to_dict()

    @app.post("/api/models")
    async def get_models(payload: Dict[str, Any]):
        config = prepare_api_configs_for_save(
            [payload],
            load_api_configs(str(app.state.api_config_path)),
        )[0]
        resolved = resolve_api_config(config)
        if not resolved.get("url") or not resolved.get("key"):
            raise HTTPException(status_code=400, detail="API url and key are required")
        models, error = await fetch_available_models(resolved["url"], resolved["key"])
        if error:
            raise HTTPException(status_code=400, detail=error)
        return {"items": models}

    @app.post("/api/browse/directory")
    async def browse_directory(payload: Dict[str, Any] | None = None):
        try:
            path = await asyncio.to_thread(
                pick_directory,
                _browse_title(payload, "选择文件夹"),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"path": path}

    @app.post("/api/uploads")
    async def upload_text_files(payload: Dict[str, Any]):
        incoming_files = payload.get("files") or []
        try:
            metadata = project_service().upload_text_files(
                project_name=str(payload.get("project_name", "")),
                project_slug=str(payload.get("project_slug", "")),
                workflow_type=str(payload.get("workflow_type", "")),
                files=incoming_files,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        uploaded_items = metadata.uploads[-len(incoming_files):] if incoming_files else []
        return {
            "project": project_to_response(metadata),
            "items": [upload.to_dict() for upload in uploaded_items],
            "workflow_output_directory": str(
                project_service().default_export_dir(
                    metadata.project_slug,
                    metadata.workflow_type,
                )
            ),
        }

    @app.get("/api/projects")
    async def list_projects(workflow_type: str = ""):
        items = [project_to_response(metadata) for metadata in project_service().list_projects(workflow_type)]
        return {"items": items}

    @app.post("/api/projects/import")
    async def import_project(payload: Dict[str, Any]):
        try:
            metadata = project_service().import_project_directory(
                source_directory=str(payload.get("path", "")),
                workflow_type=str(payload.get("workflow_type", "")),
                project_name=str(payload.get("project_name", "")),
            )
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return project_to_response(metadata)

    @app.get("/api/projects/{project_slug}")
    async def get_project(project_slug: str):
        try:
            return project_to_response(project_service().load_project(project_slug))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.patch("/api/projects/{project_slug}")
    async def update_project(project_slug: str, payload: Dict[str, Any]):
        try:
            metadata = project_service().rename_project(
                project_slug,
                str(payload.get("project_name", "")),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return project_to_response(metadata)

    @app.delete("/api/projects/{project_slug}")
    async def delete_project(project_slug: str):
        try:
            project_service().delete_project(project_slug)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return {"ok": True, "project_slug": project_slug}

    @app.delete("/api/projects/{project_slug}/uploads")
    async def clear_project_uploads(project_slug: str):
        try:
            metadata = project_service().clear_project_uploads(project_slug)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return project_to_response(metadata)

    @app.post("/api/projects/open-directory")
    async def open_project_directory(payload: Dict[str, Any]):
        service = project_service()
        project_slug = str(payload.get("project_slug", "")).strip()
        workflow_type = str(payload.get("workflow_type", "")).strip()
        requested_output_directory = _payload_custom_output(payload)
        explicit_path = str(payload.get("path", "")).strip()
        try:
            if project_slug:
                metadata = service.load_project(project_slug)
                if not workflow_type:
                    workflow_type = metadata.workflow_type
                directory, effective_custom = service.resolve_output_selection(
                    project_slug=project_slug,
                    workflow_type=workflow_type,
                    custom_output_directory=requested_output_directory or metadata.custom_output_directory,
                    create=False,
                )
                if not effective_custom:
                    directory = service.default_export_dir(project_slug, workflow_type, create=True)
                service.open_directory(directory, create=False)
                return {"ok": True, "path": str(directory)}
            if not explicit_path:
                raise ValueError("path or project_slug is required")
            service.open_directory(explicit_path, create=False)
            return {"ok": True, "path": explicit_path}
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/utils/resolve-path")
    async def resolve_path(payload: Dict[str, Any] | None = None):
        path_str = str((payload or {}).get("path", "")).strip()
        if not path_str:
            return {"path": path_str, "resolved": False, "is_directory": False}

        path, should_return_normalized_path = _normalize_user_path_value(path_str)
        exists = path.exists()
        is_directory = exists and path.is_dir()
        if should_return_normalized_path or exists:
            response = {
                "path": str(path),
                "resolved": is_directory,
                "is_directory": is_directory,
            }
        else:
            response = {"path": path_str, "resolved": False, "is_directory": False}
        return response

    async def _start_task(task_type: TaskType, request):
        try:
            request.validate()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        configs = load_api_configs(str(app.state.api_config_path))
        api_configs = select_api_configs(
            configs,
            getattr(request, "active_api_ids", None),
        )
        if task_type in {TaskType.NOVEL_SUMMARY, TaskType.ARTICLE_SUMMARY} and not api_configs:
            raise HTTPException(status_code=400, detail="At least one active API config is required")
        if task_type == TaskType.NOVEL_SUMMARY:
            runner = create_novel_summary_runner(request, api_configs)
        elif task_type == TaskType.ARTICLE_SUMMARY:
            runner = create_article_summary_runner(request, api_configs)
        elif task_type == TaskType.CHAPTER_SPLIT:
            runner = create_splitter_runner(request)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported task type: {task_type}")
        record = await app.state.runtime.start_task(
            task_type,
            wrap_runner_with_project_status(runner, request),
            params_summary=request.__dict__,
        )
        if getattr(request, "project_slug", ""):
            project_service().update_project_output(
                request.project_slug,
                project_name=getattr(request, "project_name", ""),
                custom_output_directory=getattr(request, "custom_output_directory_path", ""),
                latest_task_id=record.task_id,
                latest_task_status=record.status.value,
            )
        return _record_response(record)

    @app.post("/api/tasks/novel")
    async def start_novel_task(payload: Dict[str, Any]):
        source_folder_path = str(payload.get("source_folder_path", ""))
        output_dir: Path | None = None
        if _payload_file_ids(payload):
            try:
                _, _, _, output_dir, uploads = resolve_project_uploads(
                    payload,
                    TaskType.NOVEL_SUMMARY,
                )
                project_service().prepare_copied_inputs(output_dir=output_dir, uploads=uploads)
                source_folder_path = str(output_dir)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        request = NovelSummaryRequest(
            source_folder_path=source_folder_path,
            active_api_ids=list(payload.get("active_api_ids", [])),
            big_summary_batch_size=payload.get("big_summary_batch_size", 5),
            super_summary_threshold=payload.get("super_summary_threshold", 5),
            ultimate_api_id=str(payload.get("ultimate_api_id", "")),
            use_fine_grained_flow=bool(payload.get("use_fine_grained_flow", False)),
            word_counts=NovelWordCounts.from_dict(payload.get("word_counts") or {}),
        )
        add_project_fields(request, payload, output_dir)
        return await _start_task(TaskType.NOVEL_SUMMARY, request)

    @app.post("/api/tasks/article")
    async def start_article_task(payload: Dict[str, Any]):
        source_folder_path = str(payload.get("source_folder_path", ""))
        selected_files = list(payload.get("selected_files", []))
        output_subfolder = str(payload.get("output_subfolder", ""))
        output_dir: Path | None = None
        if _payload_file_ids(payload):
            try:
                _, _, _, output_dir, uploads = resolve_project_uploads(
                    payload,
                    TaskType.ARTICLE_SUMMARY,
                )
                selected_files = project_service().prepare_copied_inputs(
                    output_dir=output_dir,
                    uploads=uploads,
                )
                source_folder_path = str(output_dir)
                output_subfolder = ""
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        request = ArticleSummaryRequest(
            source_folder_path=source_folder_path,
            selected_files=selected_files,
            output_subfolder=output_subfolder,
            word_counts=ArticleWordCounts.from_dict(payload.get("word_counts") or {}),
        )
        add_project_fields(request, payload, output_dir)
        return await _start_task(TaskType.ARTICLE_SUMMARY, request)

    @app.post("/api/tasks/custom")
    async def start_custom_task(payload: Dict[str, Any]):
        selected_file_paths = list(payload.get("selected_file_paths", []))
        output_dir: Path | None = None
        if _payload_file_ids(payload):
            try:
                _, _, _, output_dir, uploads = resolve_project_uploads(
                    payload,
                    TaskType.CUSTOM_SUMMARY,
                )
                selected_file_paths = [upload.path for upload in uploads]
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        request = CustomSummaryRequest(
            selected_file_paths=selected_file_paths,
            user_prompt=str(payload.get("user_prompt", "")),
            api_id=str(payload.get("api_id", "")),
        )
        add_project_fields(request, payload, output_dir)
        try:
            request.validate()
            api_config = find_api_config(load_api_configs(str(app.state.api_config_path)), request.api_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        record = await app.state.runtime.start_task(
            TaskType.CUSTOM_SUMMARY,
            wrap_runner_with_project_status(
                create_custom_summary_runner(request, api_config),
                request,
            ),
            params_summary=request.__dict__,
        )
        if request.project_slug:
            project_service().update_project_output(
                request.project_slug,
                project_name=request.project_name,
                custom_output_directory=request.custom_output_directory_path,
                latest_task_id=record.task_id,
                latest_task_status=record.status.value,
            )
        return _record_response(record)

    @app.post("/api/tasks/splitter")
    async def start_splitter_task(payload: Dict[str, Any]):
        source_txt_file_path = str(payload.get("source_txt_file_path", ""))
        output_directory_path = str(payload.get("output_directory_path", ""))
        output_dir: Path | None = None
        if _payload_file_ids(payload):
            try:
                _, _, _, output_dir, uploads = resolve_project_uploads(
                    payload,
                    TaskType.CHAPTER_SPLIT,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            if len(uploads) != 1:
                raise HTTPException(status_code=400, detail="章节分割只能选择一个源 TXT 文件")
            source_txt_file_path = uploads[0].path
            output_directory_path = str(output_dir)
        request = SplitterRequest(
            source_txt_file_path=source_txt_file_path,
            output_directory_path=output_directory_path,
            mode=str(payload.get("mode", "default")),
            chapters_per_file=payload.get("chapters_per_file", 1),
            custom_pattern=str(payload.get("custom_pattern", "")),
            title_list=list(payload.get("title_list", [])),
            handle_volumes=bool(payload.get("handle_volumes", True)),
        )
        add_project_fields(request, payload, output_dir)
        return await _start_task(TaskType.CHAPTER_SPLIT, request)

    @app.get("/api/tasks")
    async def list_tasks():
        records = sorted(
            app.state.runtime.list_tasks(),
            key=lambda record: record.created_at,
            reverse=True,
        )
        return {"items": [_record_response(record) for record in records]}

    @app.get("/api/tasks/{task_id}")
    async def get_task(task_id: str):
        record = app.state.runtime.get_task(task_id)
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        return _record_response(record)

    @app.post("/api/tasks/{task_id}/pause")
    async def pause_task(task_id: str):
        try:
            return _record_response(app.state.runtime.pause_task(task_id))
        except KeyError:
            raise HTTPException(status_code=404, detail="Task not found")

    @app.post("/api/tasks/{task_id}/resume")
    async def resume_task(task_id: str):
        try:
            return _record_response(app.state.runtime.resume_task(task_id))
        except KeyError:
            raise HTTPException(status_code=404, detail="Task not found")

    @app.post("/api/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str):
        try:
            return _record_response(app.state.runtime.cancel_task(task_id))
        except KeyError:
            raise HTTPException(status_code=404, detail="Task not found")

    @app.get("/api/tasks/{task_id}/events")
    async def task_events(task_id: str):
        if not app.state.runtime.get_task(task_id):
            raise HTTPException(status_code=404, detail="Task not found")

        async def stream():
            while True:
                event = await app.state.runtime.next_event(task_id)
                yield f"data: {json.dumps(event.to_dict(), ensure_ascii=False)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    frontend_dist = app.state.frontend_dist_dir
    index_file = frontend_dist / "index.html"
    assets_dir = frontend_dist / "assets"
    if index_file.exists():
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/")
        async def webui_index():
            return FileResponse(index_file)

    else:

        @app.get("/")
        async def webui_missing():
            return HTMLResponse(
                "<h1>NovelSummaryAssistant WebUI</h1>"
                "<p>请先在 frontend 目录运行 npm install 和 npm run build，"
                "或开发模式运行 npm run dev。</p>",
                status_code=200,
            )

    return app


app = create_app()
