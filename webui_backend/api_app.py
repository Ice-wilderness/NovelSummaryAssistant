from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from logic.trigger_scan import validate_scan_startup
from logic.trigger_scan.reporting import TriggerScanReportStore

from .config_models import TriggerScanRequest
from .config_service import load_api_configs, load_user_settings
from .file_services import ensure_prompt_cache_dir, get_project_root, get_runtime_base_path
from .pattern_config_service import PatternConfigService, default_pattern_config_path
from .project_workspace import ProjectWorkspaceService, UploadedFileRef, _status_from_progress
from .task_runtime import TaskRuntime, TaskType
from .trigger_profile_service import TriggerProfileService, default_trigger_profile_dir
from .trigger_models import TriggerScanConfig
from .routes.config_routes import register_config_routes
from .routes.context import RouteContext
from .routes.profile_pattern_routes import register_profile_pattern_routes
from .routes.project_routes import register_project_routes
from .routes.summary_task_routes import register_summary_task_routes
from .routes.trigger_scan_routes import register_trigger_scan_routes


def _default_api_config_path() -> Path:
    return get_project_root() / "api_configs.json"


def _default_frontend_dist_dir() -> Path:
    return get_project_root() / "frontend" / "dist"


def _default_user_settings_path(runtime_base_path: Path) -> Path:
    return runtime_base_path / "user_settings.json"


def _task_result_status(result_summary: str | None) -> str:
    normalized = str(result_summary or "").strip().lower()
    if normalized == "failed" or normalized.startswith("error:"):
        return "failed"
    return "success"


TERMINAL_TASK_STATUSES = {"success", "failed", "cancelled", "partial_failed"}


def _is_terminal_status(status: str | None) -> bool:
    return str(status or "").strip().lower() in TERMINAL_TASK_STATUSES


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
        is_terminal_status=_is_terminal_status,
        payload_file_ids=_payload_file_ids,
        payload_project_slug=_payload_project_slug,
        payload_project_name=_payload_project_name,
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
    register_trigger_scan_routes(context)
    register_summary_task_routes(context)

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
