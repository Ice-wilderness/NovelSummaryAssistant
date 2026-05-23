from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from logic.llm_api import fetch_available_models
from logic.paragraph_index import build_chapter_paragraph_index, extract_paragraph_context
from logic.trigger_scan import validate_scan_startup
from logic.trigger_scan.reporting import SkipListStore, TriggerScanReportStore

from .config_models import (
    ApiConfig,
    ArticleWordCounts,
    ArticleSummaryRequest,
    CustomSummaryRequest,
    NovelSummaryRequest,
    NovelWordCounts,
    SplitterRequest,
    TriggerScanRequest,
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
from .local_picker import pick_directory, pick_file
from .project_workspace import ProjectWorkspaceService, UploadedFileRef
from .task_runtime import TaskRuntime, TaskType
from .trigger_profile_service import TriggerProfileService, default_trigger_profile_dir
from .workflow_services import (
    create_article_summary_runner,
    create_custom_summary_runner,
    create_trigger_scan_runner,
    create_novel_summary_runner,
    create_splitter_runner,
    find_api_config,
    select_api_configs,
)
from .trigger_models import SkipListItem, TriggerScanConfig


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
    trigger_profile_dir: str | Path | None = None,
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
    app.state.trigger_profile_dir = (
        Path(trigger_profile_dir)
        if trigger_profile_dir
        else default_trigger_profile_dir(app.state.runtime_base_path)
    )

    def project_service() -> ProjectWorkspaceService:
        settings = load_user_settings(str(app.state.user_settings_path))
        return ProjectWorkspaceService(
            app.state.runtime_base_path,
            default_export_directory=settings.default_export_directory,
        )

    def trigger_profile_service() -> TriggerProfileService:
        return TriggerProfileService(profile_dir=app.state.trigger_profile_dir)

    SUMMARY_SCAN_TASK_TYPES = {
        TaskType.NOVEL_SUMMARY.value,
        TaskType.SMALL_SUMMARY_PREPARATION.value,
        TaskType.ARTICLE_SUMMARY.value,
        TaskType.CUSTOM_SUMMARY.value,
        TaskType.TRIGGER_SCAN.value,
    }

    def ensure_summary_scan_available(task_type: TaskType) -> None:
        if task_type == TaskType.TRIGGER_SCAN:
            if app.state.runtime.has_active_task(SUMMARY_SCAN_TASK_TYPES):
                raise HTTPException(
                    status_code=409,
                    detail="已有总结或雷点扫描任务正在运行，请等待任务结束后再开始",
                )
            return
        if task_type.value in SUMMARY_SCAN_TASK_TYPES:
            if app.state.runtime.has_active_task({TaskType.TRIGGER_SCAN.value}):
                raise HTTPException(
                    status_code=409,
                    detail="已有雷点扫描任务正在运行，请等待任务结束后再开始",
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
        service.refresh_granularity_metadata(metadata)
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
                    summary_output_format=getattr(request, "summary_output_format", ""),
                )
                return result
            except asyncio.CancelledError:
                project_service().update_project_output(
                    request.project_slug,
                    project_name=getattr(request, "project_name", ""),
                    custom_output_directory=getattr(request, "custom_output_directory_path", ""),
                    latest_task_id=record.task_id,
                    latest_task_status="cancelled",
                    summary_output_format=getattr(request, "summary_output_format", ""),
                )
                raise
            except Exception:
                project_service().update_project_output(
                    request.project_slug,
                    project_name=getattr(request, "project_name", ""),
                    custom_output_directory=getattr(request, "custom_output_directory_path", ""),
                    latest_task_id=record.task_id,
                    latest_task_status="failed",
                    summary_output_format=getattr(request, "summary_output_format", ""),
                )
                raise

        return wrapped

    def resolve_trigger_scan_request(
        payload: Dict[str, Any],
        *,
        create_output: bool,
    ):
        project_slug = _payload_project_slug(payload)
        if not project_slug:
            raise ValueError("project_slug is required")
        service = project_service()
        metadata = service.load_project(project_slug)
        if metadata.workflow_type not in {"novel_summary", "chapter_split"}:
            raise ValueError("雷点扫描只能用于小说总结或章节分割项目")
        service.refresh_granularity_metadata(metadata)
        if metadata.requires_granularity_migration:
            raise ValueError("项目包含旧版多章合并文件，请先完成章节粒度迁移")
        requested_custom_output = _payload_custom_output(payload) or metadata.custom_output_directory
        output_dir, effective_custom = service.resolve_output_selection(
            project_slug=metadata.project_slug,
            workflow_type=metadata.workflow_type,
            custom_output_directory=requested_custom_output,
            create=create_output,
        )
        profile_id = str(payload.get("profile_id") or payload.get("trigger_profile_id") or "").strip()
        profile_service = trigger_profile_service()
        profile_service.list_profiles()
        profile = profile_service.load_profile(profile_id)
        scan_config = TriggerScanConfig.from_dict(payload.get("scan_config") or payload)
        resume_from_report_id = str(payload.get("resume_from_report_id", "")).strip()
        request = TriggerScanRequest(
            project_slug=metadata.project_slug,
            project_name=metadata.project_name,
            source_folder_path=str(output_dir),
            project_output_directory_path=str(output_dir),
            profile_id=profile.id,
            scan_config=scan_config,
            custom_output_directory_path=effective_custom,
            managed_output_directory_path="" if effective_custom else str(output_dir),
            resume_from_report_id=resume_from_report_id,
        )
        return request, profile, metadata, output_dir

    def trigger_scan_validation_payload(request: TriggerScanRequest, profile) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            request.validate()
        except ValueError as exc:
            errors.append(str(exc))
        active_api_ids = [
            config.id
            for config in load_api_configs(str(app.state.api_config_path))
            if config.is_active
        ]
        # When resuming, use the original report's config for compatibility check
        resume_snapshot = None
        if request.resume_from_report_id:
            try:
                store, _output_dir, _metadata = trigger_report_store_for_project(request.project_slug)
                report = store.load_report(request.resume_from_report_id)
                resume_snapshot = report.scan_config.to_dict()
            except (ValueError, OSError):
                pass
        startup = validate_scan_startup(
            novel_folder_path=request.source_folder_path,
            profile=profile,
            config=request.scan_config,
            available_api_ids=active_api_ids,
            resume_from_report_id=request.resume_from_report_id,
            config_snapshot=resume_snapshot,
            profile_version=str(profile.updated_at or profile.created_at or profile.id),
        )
        errors.extend(startup.errors)
        decisions = []
        if any("migration" in error for error in errors):
            decisions.extend(["migrate_chapter_granularity", "cancel"])
        if startup.resumable_state is not None and startup.pending_chapter_files:
            decisions.append("resume_scan")
        try:
            scan_config_payload = request.scan_config.to_dict()
        except ValueError:
            scan_config_payload = {
                **dict(request.scan_config.__dict__),
                "scan_range": dict(request.scan_config.scan_range.__dict__),
            }
        return {
            "ready": not errors,
            "errors": errors,
            "warnings": startup.warnings,
            "decisions": sorted(set(decisions)),
            "chapter_count": len(startup.chapter_files),
            "selected_chapter_count": len(startup.selected_chapter_files),
            "pending_chapter_count": len(startup.pending_chapter_files),
            "completed_chapter_count": len(startup.resumable_state.completed_chapters) if startup.resumable_state else 0,
            "chapter_files": startup.chapter_files,
            "selected_chapter_files": startup.selected_chapter_files,
            "scan_config": scan_config_payload,
        }

    def trigger_report_store_for_project(project_slug: str, *, create: bool = False):
        metadata = project_service().load_project(project_slug)
        output_dir, _ = project_service().resolve_output_selection(
            project_slug=metadata.project_slug,
            workflow_type=metadata.workflow_type,
            custom_output_directory=metadata.custom_output_directory,
            create=create,
        )
        return TriggerScanReportStore(output_dir), output_dir, metadata

    def skip_list_store_for_project(project_slug: str, *, create: bool = False):
        metadata = project_service().load_project(project_slug)
        output_dir, _ = project_service().resolve_output_selection(
            project_slug=metadata.project_slug,
            workflow_type=metadata.workflow_type,
            custom_output_directory=metadata.custom_output_directory,
            create=create,
        )
        return SkipListStore(output_dir, metadata.project_slug), output_dir, metadata

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

    @app.get("/api/trigger-profiles")
    async def list_trigger_profiles():
        profiles = trigger_profile_service().list_profiles()
        return {"items": [profile.to_dict() for profile in profiles]}

    @app.post("/api/trigger-profiles")
    async def create_trigger_profile(payload: Dict[str, Any]):
        try:
            profile = trigger_profile_service().create_profile(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.post("/api/trigger-profiles/import")
    async def import_trigger_profile(payload: Dict[str, Any]):
        try:
            profile = trigger_profile_service().import_profile(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.get("/api/trigger-profiles/{profile_id}")
    async def get_trigger_profile(profile_id: str):
        try:
            profile = trigger_profile_service().load_profile(profile_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return profile.to_dict()

    @app.patch("/api/trigger-profiles/{profile_id}")
    async def update_trigger_profile(profile_id: str, payload: Dict[str, Any]):
        try:
            profile = trigger_profile_service().update_profile(profile_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.post("/api/trigger-profiles/{profile_id}/duplicate")
    async def duplicate_trigger_profile(profile_id: str, payload: Dict[str, Any] | None = None):
        try:
            profile = trigger_profile_service().duplicate_profile(profile_id, payload or {})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.delete("/api/trigger-profiles/{profile_id}")
    async def delete_trigger_profile(profile_id: str):
        try:
            trigger_profile_service().delete_profile(profile_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return {"status": "deleted", "profile_id": profile_id}

    @app.post("/api/trigger-profiles/{profile_id}/groups")
    async def add_trigger_rule_group(profile_id: str, payload: Dict[str, Any]):
        try:
            profile = trigger_profile_service().add_rule_group(profile_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.patch("/api/trigger-profiles/{profile_id}/groups/{group_id}")
    async def update_trigger_rule_group(
        profile_id: str,
        group_id: str,
        payload: Dict[str, Any],
    ):
        try:
            profile = trigger_profile_service().update_rule_group(profile_id, group_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.delete("/api/trigger-profiles/{profile_id}/groups/{group_id}")
    async def delete_trigger_rule_group(profile_id: str, group_id: str):
        try:
            profile = trigger_profile_service().delete_rule_group(profile_id, group_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.post("/api/trigger-profiles/{profile_id}/rules")
    async def add_trigger_rule(profile_id: str, payload: Dict[str, Any]):
        try:
            profile = trigger_profile_service().add_rule(profile_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.patch("/api/trigger-profiles/{profile_id}/rules/{rule_id}")
    async def update_trigger_rule(
        profile_id: str,
        rule_id: str,
        payload: Dict[str, Any],
    ):
        try:
            profile = trigger_profile_service().update_rule(profile_id, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.delete("/api/trigger-profiles/{profile_id}/rules/{rule_id}")
    async def delete_trigger_rule(profile_id: str, rule_id: str):
        try:
            profile = trigger_profile_service().delete_rule(profile_id, rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

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

    @app.post("/api/browse/file")
    async def browse_file(payload: Dict[str, Any] | None = None):
        try:
            path = await asyncio.to_thread(
                pick_file,
                _browse_title(payload, "选择文件"),
                (("文本文件", "*.txt"), ("所有文件", "*.*")),
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
            metadata = project_service().save_project_draft(
                project_slug,
                project_name=str(payload.get("project_name", "")),
                uploaded_file_ids=payload.get("uploaded_file_ids"),
                custom_output_directory=_payload_custom_output(payload),
                migrate_existing_output=bool(payload.get("migrate_existing_output", False)),
                summary_output_format=str(payload.get("summary_output_format") or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return project_to_response(metadata)

    @app.post("/api/projects/{project_slug}/output-migration-check")
    async def check_project_output_migration(project_slug: str, payload: Dict[str, Any]):
        try:
            return project_service().output_migration_info(
                project_slug,
                custom_output_directory=_payload_custom_output(payload),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/projects/{project_slug}/chapter-granularity-migration")
    async def check_chapter_granularity_migration(project_slug: str):
        try:
            return project_service().check_chapter_granularity_migration(project_slug)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/projects/{project_slug}/chapter-granularity-migration")
    async def migrate_chapter_granularity(project_slug: str, payload: Dict[str, Any] | None = None):
        try:
            metadata, migration = project_service().migrate_chapter_granularity(
                project_slug,
                source_txt_file_path=str((payload or {}).get("source_txt_file_path", "")),
            )
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"project": project_to_response(metadata), "migration": migration}

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
        ensure_summary_scan_available(task_type)
        try:
            request.validate()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        settings = load_user_settings(str(app.state.user_settings_path))
        configs = load_api_configs(str(app.state.api_config_path))
        api_configs = select_api_configs(
            configs,
            getattr(request, "active_api_ids", None),
        )
        for api_config in api_configs:
            api_config["minimum_output_characters"] = settings.minimum_output_characters
        if (
            task_type
            in {TaskType.NOVEL_SUMMARY, TaskType.SMALL_SUMMARY_PREPARATION, TaskType.ARTICLE_SUMMARY}
            and not api_configs
        ):
            raise HTTPException(status_code=400, detail="At least one active API config is required")
        if task_type in {TaskType.NOVEL_SUMMARY, TaskType.SMALL_SUMMARY_PREPARATION}:
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
                summary_output_format=getattr(request, "summary_output_format", ""),
            )
        return _record_response(record)

    async def _start_novel_task_from_payload(
        payload: Dict[str, Any],
        task_type: TaskType,
        *,
        force_stop_after_small_summary: bool = False,
    ):
        source_folder_path = str(payload.get("source_folder_path", ""))
        output_dir: Path | None = None
        project_slug_for_start = _payload_project_slug(payload)
        project_metadata_for_start = None
        if project_slug_for_start:
            try:
                metadata = project_service().load_project(project_slug_for_start)
                project_service().refresh_granularity_metadata(metadata)
                project_metadata_for_start = metadata
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            if metadata.requires_granularity_migration:
                raise HTTPException(status_code=400, detail="项目包含旧版多章合并文件，请先完成章节粒度迁移")
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
            summary_batch_size=payload.get("summary_batch_size", 10),
            summary_output_format=str(
                payload.get("summary_output_format")
                or (
                    project_metadata_for_start.summary_output_format
                    if project_metadata_for_start
                    else "md"
                )
            ),
            big_summary_batch_size=payload.get("big_summary_batch_size", 5),
            super_summary_threshold=payload.get("super_summary_threshold", 5),
            ultimate_api_id=str(payload.get("ultimate_api_id", "")),
            use_fine_grained_flow=bool(payload.get("use_fine_grained_flow", False)),
            stop_after_small_summary=(
                force_stop_after_small_summary
                or bool(payload.get("stop_after_small_summary", False))
            ),
            word_counts=NovelWordCounts.from_dict(payload.get("word_counts") or {}),
        )
        add_project_fields(request, payload, output_dir)
        return await _start_task(task_type, request)

    @app.post("/api/trigger-scan/precheck")
    async def precheck_trigger_scan(payload: Dict[str, Any]):
        try:
            request, profile, _metadata, _output_dir = resolve_trigger_scan_request(
                payload,
                create_output=False,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return trigger_scan_validation_payload(request, profile)

    @app.get("/api/trigger-scan/projects/{project_slug}/config")
    async def get_trigger_scan_config(project_slug: str):
        try:
            metadata = project_service().load_project(project_slug)
            output_dir, _effective = project_service().resolve_output_selection(
                project_slug=metadata.project_slug,
                workflow_type=metadata.workflow_type,
                custom_output_directory=metadata.custom_output_directory,
                create=False,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        config_path = Path(output_dir) / "trigger_scan" / "scan_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return TriggerScanConfig().to_dict()

    @app.put("/api/trigger-scan/projects/{project_slug}/config")
    async def save_trigger_scan_config(project_slug: str, payload: Dict[str, Any]):
        try:
            metadata = project_service().load_project(project_slug)
            output_dir, _effective = project_service().resolve_output_selection(
                project_slug=metadata.project_slug,
                workflow_type=metadata.workflow_type,
                custom_output_directory=metadata.custom_output_directory,
                create=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        config = TriggerScanConfig.from_dict(payload)
        config.validate()
        config_path = Path(output_dir) / "trigger_scan" / "scan_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = config_path.with_suffix(config_path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        tmp.replace(config_path)
        return config.to_dict()

    @app.post("/api/tasks/trigger-scan")
    async def start_trigger_scan_task(payload: Dict[str, Any]):
        ensure_summary_scan_available(TaskType.TRIGGER_SCAN)
        try:
            request, profile, _metadata, _output_dir = resolve_trigger_scan_request(
                payload,
                create_output=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        validation = trigger_scan_validation_payload(request, profile)
        if not validation["ready"]:
            raise HTTPException(status_code=400, detail=validation)

        configs = load_api_configs(str(app.state.api_config_path))
        settings = load_user_settings(str(app.state.user_settings_path))
        scan_api_configs = select_api_configs(configs, request.scan_config.scan_api_ids)
        requested_scan_ids = set(request.scan_config.scan_api_ids)
        selected_scan_ids = {config["id"] for config in scan_api_configs}
        missing_scan_ids = sorted(requested_scan_ids - selected_scan_ids)
        if missing_scan_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown or inactive scan API: {', '.join(missing_scan_ids)}",
            )
        for api_config in scan_api_configs:
            api_config["minimum_output_characters"] = request.scan_config.minimum_output_characters
        verification_api_config = None
        if request.scan_config.verification_api_id:
            verification_matches = select_api_configs(
                configs,
                [request.scan_config.verification_api_id],
            )
            if not verification_matches:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown or inactive verification API: {request.scan_config.verification_api_id}",
                )
            verification_api_config = verification_matches[0]
            verification_api_config["minimum_output_characters"] = request.scan_config.minimum_output_characters

        runner = create_trigger_scan_runner(
            request,
            profile,
            scan_api_configs,
            verification_api_config=verification_api_config,
        )
        record = await app.state.runtime.start_task(
            TaskType.TRIGGER_SCAN,
            wrap_runner_with_project_status(runner, request),
            params_summary={
                **request.__dict__,
                "scan_config": request.scan_config.to_dict(),
            },
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

    @app.get("/api/trigger-scan/tasks/{task_id}")
    async def get_trigger_scan_task(task_id: str):
        record = app.state.runtime.get_task(task_id)
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        return _record_response(record)

    @app.get("/api/trigger-scan/projects/{project_slug}/reports")
    async def list_trigger_scan_reports(project_slug: str):
        try:
            store, _output_dir, _metadata = trigger_report_store_for_project(project_slug)
            return {"items": [entry.to_dict() for entry in store.list_reports()]}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/api/trigger-scan/projects/{project_slug}/reports/{report_id}")
    async def get_trigger_scan_report(project_slug: str, report_id: str):
        try:
            store, _output_dir, _metadata = trigger_report_store_for_project(project_slug)
            return store.load_report(report_id).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.delete("/api/trigger-scan/projects/{project_slug}/reports/{report_id}")
    async def delete_trigger_scan_report(project_slug: str, report_id: str):
        try:
            store, _output_dir, _metadata = trigger_report_store_for_project(project_slug, create=True)
            store.delete_report(report_id)
            return {"ok": True, "report_id": report_id}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.patch("/api/trigger-scan/projects/{project_slug}/reports/{report_id}/findings/{finding_id}")
    async def update_trigger_scan_finding(
        project_slug: str,
        report_id: str,
        finding_id: str,
        payload: Dict[str, Any],
    ):
        try:
            store, _output_dir, _metadata = trigger_report_store_for_project(project_slug, create=True)
            finding = store.update_finding_review(
                report_id,
                finding_id,
                review_status=payload.get("review_status"),
                user_note=payload.get("user_note"),
            )
            return finding.to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/trigger-scan/projects/{project_slug}/reports/{report_id}/findings/{finding_id}/skip-list")
    async def add_trigger_scan_finding_to_skip_list(
        project_slug: str,
        report_id: str,
        finding_id: str,
        payload: Dict[str, Any] | None = None,
    ):
        try:
            report_store, output_dir, metadata = trigger_report_store_for_project(project_slug, create=True)
            report = report_store.load_report(report_id)
            finding = next(
                (item for item in report.findings if item.finding_id == finding_id),
                None,
            )
            if finding is None:
                raise ValueError(f"Unknown finding: {finding_id}")
            note = str((payload or {}).get("user_note") or finding.user_note)
            item = SkipListItem(
                chapter_file=finding.chapter_file,
                chapter_title=finding.chapter_title,
                paragraph_range=", ".join(finding.paragraph_ids),
                rule_name=finding.rule_name,
                severity=finding.severity,
                user_note=note,
                source_finding_id=finding.finding_id,
            )
            skip_list = SkipListStore(output_dir, metadata.project_slug).add_item(item)
            finding.in_skip_list = True
            report_store.save_report(report)
            return skip_list.to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/trigger-scan/projects/{project_slug}/reports/{report_id}/findings/{finding_id}/context")
    async def get_trigger_scan_finding_context(
        project_slug: str,
        report_id: str,
        finding_id: str,
        before: int = 1,
        after: int = 1,
    ):
        try:
            store, output_dir, _metadata = trigger_report_store_for_project(project_slug)
            report = store.load_report(report_id)
            finding = next(
                (item for item in report.findings if item.finding_id == finding_id),
                None,
            )
            if finding is None:
                raise ValueError(f"Unknown finding: {finding_id}")
            chapter_path = Path(finding.chapter_file)
            if not chapter_path.is_absolute():
                chapter_path = output_dir / finding.chapter_file
            if not chapter_path.exists():
                return {
                    "ok": False,
                    "warning": f"章节文件不存在：{finding.chapter_file}",
                }
            chapter_index = build_chapter_paragraph_index(
                chapter_path,
                novel_folder_path=output_dir,
            )
            context = extract_paragraph_context(
                chapter_index,
                finding.paragraph_ids,
                before=before,
                after=after,
            )
            return {
                "ok": True,
                "chapter_file": chapter_index.chapter_file,
                "chapter_title": chapter_index.chapter_title,
                "matched_paragraph_ids": context.matched_paragraph_ids,
                "missing_paragraph_ids": context.missing_paragraph_ids,
                "paragraphs": [
                    {
                        "id": paragraph.id,
                        "text": paragraph.text,
                        "line_number": paragraph.line_number,
                        "matched": paragraph.id in context.matched_paragraph_ids,
                    }
                    for paragraph in context.paragraphs
                ],
                "text": context.text,
            }
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/trigger-scan/projects/{project_slug}/reports/{report_id}/export")
    async def export_trigger_scan_report(project_slug: str, report_id: str, payload: Dict[str, Any]):
        export_format = str(payload.get("format") or "md").strip().lower()
        try:
            store, _output_dir, _metadata = trigger_report_store_for_project(project_slug, create=True)
            if export_format == "json":
                path = store.export_report_json(report_id)
            elif export_format in {"md", "markdown"}:
                path = store.export_report_markdown(report_id)
            else:
                raise ValueError("format must be one of: md, json")
            return {"path": str(path), "format": export_format}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/trigger-scan/projects/{project_slug}/skip-list")
    async def get_trigger_scan_skip_list(project_slug: str):
        try:
            store, _output_dir, _metadata = skip_list_store_for_project(project_slug)
            skip_list = store.load()
            return {
                **skip_list.to_dict(),
                "grouped": {
                    chapter: [item.to_dict() for item in items]
                    for chapter, items in store.group_by_chapter().items()
                },
            }
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.post("/api/trigger-scan/projects/{project_slug}/skip-list")
    async def add_trigger_scan_skip_item(project_slug: str, payload: Dict[str, Any]):
        try:
            store, _output_dir, _metadata = skip_list_store_for_project(project_slug, create=True)
            return store.add_item(SkipListItem.from_dict(payload)).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.patch("/api/trigger-scan/projects/{project_slug}/skip-list/{source_finding_id}")
    async def update_trigger_scan_skip_item(
        project_slug: str,
        source_finding_id: str,
        payload: Dict[str, Any],
    ):
        try:
            store, _output_dir, _metadata = skip_list_store_for_project(project_slug, create=True)
            return store.update_item(source_finding_id, **payload).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.delete("/api/trigger-scan/projects/{project_slug}/skip-list/{source_finding_id}")
    async def delete_trigger_scan_skip_item(project_slug: str, source_finding_id: str):
        try:
            store, _output_dir, _metadata = skip_list_store_for_project(project_slug, create=True)
            return store.remove_item(source_finding_id).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/trigger-scan/projects/{project_slug}/skip-list/export")
    async def export_trigger_scan_skip_list(project_slug: str):
        try:
            store, _output_dir, _metadata = skip_list_store_for_project(project_slug, create=True)
            path = store.export_markdown()
            return {"path": str(path), "format": "md"}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/tasks/novel")
    async def start_novel_task(payload: Dict[str, Any]):
        return await _start_novel_task_from_payload(
            payload,
            TaskType.NOVEL_SUMMARY,
        )

    @app.post("/api/tasks/novel/small-summary")
    async def start_small_summary_preparation_task(payload: Dict[str, Any]):
        return await _start_novel_task_from_payload(
            payload,
            TaskType.SMALL_SUMMARY_PREPARATION,
            force_stop_after_small_summary=True,
        )

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
            settings = load_user_settings(str(app.state.user_settings_path))
            api_config["minimum_output_characters"] = settings.minimum_output_characters
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
