from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from logic.llm_api import fetch_available_models
from logic.paragraph_index import build_chapter_paragraph_index, extract_paragraph_context
from logic.trigger_scan import validate_scan_startup
from logic.trigger_scan.reporting import TriggerScanReportStore

from .config_models import (
    ApiConfig,
    ArticleWordCounts,
    ArticleSummaryRequest,
    ChapterPreviewItem,
    ChapterPreviewRequest,
    CustomSummaryRequest,
    NovelSummaryRequest,
    NovelWordCounts,
    PatternConfig,
    PatternConfigListResponse,
    SplitPreviewResult,
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
from .pattern_config_service import PatternConfigService, default_pattern_config_path
from .project_workspace import ProjectWorkspaceService, UploadedFileRef, _status_from_progress
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
from .trigger_models import TriggerScanConfig
from .routes.config_routes import register_config_routes
from .routes.context import RouteContext
from .routes.profile_pattern_routes import register_profile_pattern_routes
from .routes.project_routes import register_project_routes


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


TERMINAL_TASK_STATUSES = {"success", "failed", "cancelled", "partial_failed"}


def _is_terminal_status(status: str | None) -> bool:
    return str(status or "").strip().lower() in TERMINAL_TASK_STATUSES


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
    app.state.pattern_config_path = default_pattern_config_path(app.state.runtime_base_path)

    def project_service() -> ProjectWorkspaceService:
        settings = load_user_settings(str(app.state.user_settings_path))
        return ProjectWorkspaceService(
            app.state.runtime_base_path,
            default_export_directory=settings.default_export_directory,
        )

    def trigger_profile_service() -> TriggerProfileService:
        return TriggerProfileService(profile_dir=app.state.trigger_profile_dir)

    def pattern_config_service() -> PatternConfigService:
        return PatternConfigService(app.state.pattern_config_path)

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
        metadata.progress = service.scan_project_progress(metadata)
        running = False
        if metadata.latest_task_id:
            task = app.state.runtime.get_task(str(metadata.latest_task_id))
            if task:
                metadata.latest_task_status = task.status.value
                running = task.status.value in ("pending", "running", "paused")
        if not running:
            disk_status = _status_from_progress(metadata.progress)
            if disk_status:
                metadata.latest_task_status = disk_status
        service.refresh_granularity_metadata(metadata)
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

    context = RouteContext(
        app=app,
        project_service=project_service,
        trigger_profile_service=trigger_profile_service,
        pattern_config_service=pattern_config_service,
        ensure_summary_scan_available=ensure_summary_scan_available,
        project_to_response=project_to_response,
        browse_title=_browse_title,
        normalize_user_path_value=_normalize_user_path_value,
        payload_custom_output=_payload_custom_output,
        resolve_project_uploads=resolve_project_uploads,
        add_project_fields=add_project_fields,
        wrap_runner_with_project_status=wrap_runner_with_project_status,
        resolve_trigger_scan_request=resolve_trigger_scan_request,
        trigger_scan_validation_payload=trigger_scan_validation_payload,
        trigger_report_store_for_project=trigger_report_store_for_project,
    )
    register_config_routes(context)
    register_profile_pattern_routes(context)
    register_project_routes(context)

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
                project_metadata_for_start = metadata
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
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
            use_fine_grained_flow=bool(
                payload.get(
                    "use_fine_grained_flow",
                    project_metadata_for_start.use_fine_grained_flow
                    if project_metadata_for_start
                    else False,
                )
            ),
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

    @app.post("/api/chapters/preview-split")
    async def preview_chapter_split(payload: Dict[str, Any]):
        file_content = str(payload.get("file_content", ""))

        # 支持通过 uploaded_file_ids 解析文件内容
        upload_ids = _payload_file_ids(payload)
        if upload_ids and not file_content:
            try:
                _, _, _, _, uploads = resolve_project_uploads(
                    payload,
                    TaskType.CHAPTER_SPLIT,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            if len(uploads) != 1:
                raise HTTPException(status_code=400, detail="章节预览只能选择一个源 TXT 文件")
            from logic.utils import read_file_content_robustly
            try:
                file_content = read_file_content_robustly(uploads[0].path)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"读取源文件失败: {exc}")

        try:
            request = ChapterPreviewRequest(
                file_content=file_content,
                mode=str(payload.get("mode", "default")),
                pattern_config_id=str(payload.get("pattern_config_id", "")),
                title_list=list(payload.get("title_list", [])),
                handle_volumes=bool(payload.get("handle_volumes", True)),
            )
            request.validate()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        pattern_config = None
        if request.mode == "regex" and request.pattern_config_id:
            try:
                pattern_config = pattern_config_service().get(request.pattern_config_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

        from logic.chapter_splitter import preview_split as do_preview

        try:
            chapters = await asyncio.to_thread(
                do_preview,
                content=request.file_content,
                mode=request.mode,
                pattern_config=pattern_config,
                title_list=request.title_list,
                handle_volumes=request.handle_volumes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        result = SplitPreviewResult(
            chapter_count=len(chapters),
            chapters=[ChapterPreviewItem(**item) for item in chapters],
        )
        return result.to_dict()

    @app.post("/api/splitter/direct")
    async def direct_split(payload: Dict[str, Any]):
        """无状态分割：接收文件内容，切分后写入指定目录，不创建项目。"""
        import tempfile

        file_content = str(payload.get("file_content", ""))
        output_dir = str(payload.get("output_directory_path", "")).strip()
        mode = str(payload.get("mode", "default"))
        handle_volumes = bool(payload.get("handle_volumes", True))

        if not file_content:
            raise HTTPException(status_code=400, detail="请选择源文件")
        if not output_dir:
            raise HTTPException(status_code=400, detail="请指定输出目录")

        output_path = Path(output_dir).expanduser().resolve(strict=False)
        if output_path.exists() and not output_path.is_dir():
            raise HTTPException(status_code=400, detail="输出路径不是目录")

        # 解析正则配置
        custom_pattern = str(payload.get("custom_pattern", ""))
        pattern_config_id = str(payload.get("pattern_config_id", ""))
        pattern_config = None
        if mode == "regex" and pattern_config_id:
            try:
                pattern_config = pattern_config_service().get(pattern_config_id)
                if pattern_config.regex_mode == "simple":
                    custom_pattern = pattern_config.pattern
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

        title_list = list(payload.get("title_list", []))

        # 写临时文件
        tmp_path = Path(tempfile.gettempdir()) / f"novel_splitter_{int(time.time() * 1000)}.txt"
        try:
            tmp_path.write_text(file_content, encoding="utf-8")

            success, count = await asyncio.to_thread(
                split_novel_into_chapter_files,
                source_txt_file_path=str(tmp_path),
                output_directory_path=str(output_path),
                mode=mode,
                custom_pattern=custom_pattern,
                title_list=title_list,
                handle_volumes=handle_volumes,
                pattern_config=pattern_config,
            )
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

        if not success or count <= 0:
            raise HTTPException(status_code=400, detail="分割失败，未能生成章节文件")

        return {"success": True, "file_count": count, "output_directory": str(output_path)}

    @app.post("/api/tasks/splitter")
    async def start_splitter_task(payload: Dict[str, Any]):
        import tempfile

        context = str(payload.get("context", "chapter_split"))
        source_txt_file_path = str(payload.get("source_txt_file_path", ""))
        output_directory_path = str(payload.get("output_directory_path", ""))
        output_dir: Path | None = None

        # novel_summary 上下文支持 file_content 直接传入（不依赖 uploaded_file_ids）
        file_content = str(payload.get("file_content", ""))
        if context == "novel_summary" and file_content:
            project_slug = _payload_project_slug(payload)
            project_name = _payload_project_name(payload)
            if not project_slug:
                raise HTTPException(status_code=400, detail="novel_summary 上下文需要 project_slug")

            # 确保项目存在（源文件不上传时可能还没创建）
            try:
                project_service().load_project(project_slug)
            except ValueError:
                project_service().ensure_project(
                    project_name=project_name or project_slug,
                    workflow_type="novel_summary",
                    project_slug=project_slug,
                )

            split_mode = str(payload.get("mode", "default"))
            custom_pattern = str(payload.get("custom_pattern", ""))
            pattern_config_id = str(payload.get("pattern_config_id", ""))
            pattern_config = None
            if split_mode == "regex" and pattern_config_id:
                try:
                    pattern_config = pattern_config_service().get(pattern_config_id)
                    if pattern_config.regex_mode == "simple":
                        custom_pattern = pattern_config.pattern
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc))

            # 写临时文件再分割
            tmp = Path(tempfile.gettempdir()) / f"nv_split_{int(time.time() * 1000)}.txt"
            try:
                tmp.write_text(file_content, encoding="utf-8")
                metadata = project_service().split_and_ingest_source_file(
                    project_slug=project_slug,
                    source_file_path=str(tmp),
                    mode=split_mode,
                    custom_pattern=custom_pattern,
                    title_list=list(payload.get("title_list", [])),
                    handle_volumes=bool(payload.get("handle_volumes", True)),
                    pattern_config=pattern_config,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass
            return project_to_response(metadata)

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
            context=context,
            pattern_config_id=str(payload.get("pattern_config_id", "")),
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
            record = app.state.runtime.get_task(task_id)
            if record and _is_terminal_status(record.status.value):
                terminal_event = next(
                    (
                        event
                        for event in reversed(record.events)
                        if _is_terminal_status(event.status)
                    ),
                    None,
                )
                if terminal_event:
                    yield f"data: {json.dumps(terminal_event.to_dict(), ensure_ascii=False)}\n\n"
                return
            while True:
                event = await app.state.runtime.next_event(task_id)
                yield f"data: {json.dumps(event.to_dict(), ensure_ascii=False)}\n\n"
                if _is_terminal_status(event.status):
                    return

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
