from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import HTTPException

from ..config_models import NovelSummaryRequest, NovelWordCounts
from ..config_service import load_api_configs, load_user_settings
from ..local_picker import pick_directory, pick_file
from ..task_runtime import TaskRunOutcome, TaskType
from ..workflow_services import create_novel_summary_runner, select_api_configs
from .context import RouteContext


def _repair_result_status(result: Any) -> str:
    if isinstance(result, TaskRunOutcome):
        return str(getattr(result.status, "value", result.status))
    normalized = str(result or "").strip().lower()
    if normalized == "failed" or normalized.startswith("error:"):
        return "failed"
    return "success"


def _find_repair_action(plan: Dict[str, Any] | None, action_id: str) -> Dict[str, Any]:
    for action in (plan or {}).get("actions", []):
        if isinstance(action, dict) and str(action.get("action_id", "")) == action_id:
            return action
    raise ValueError("修复计划已过期，请刷新项目状态后重试。")


def _require_repair_confirmations(action: Dict[str, Any], payload: Dict[str, Any]) -> None:
    if str(action.get("status", "")) == "blocked":
        reason = str(action.get("blocked_reason") or "该修复动作当前不可用")
        raise ValueError(reason)
    if action.get("requires_llm") and not bool(payload.get("confirm_llm", False)):
        raise ValueError("该修复可能调用 LLM 并产生费用，请确认后再开始。")
    if action.get("may_change_content") and not bool(payload.get("confirm_content_change", False)):
        raise ValueError("该修复可能生成与原结果不同的内容，请确认后再开始。")
    if action.get("may_overwrite") and not bool(payload.get("confirm_overwrite", False)):
        raise ValueError("该修复可能覆盖已有文件，请确认后再开始。")


def register_project_routes(ctx: RouteContext) -> None:
    app = ctx.app

    @app.post("/api/browse/directory")
    async def browse_directory(payload: Dict[str, Any] | None = None):
        try:
            path = await asyncio.to_thread(
                pick_directory,
                ctx.browse_title(payload, "选择文件夹"),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"path": path}

    @app.post("/api/browse/file")
    async def browse_file(payload: Dict[str, Any] | None = None):
        try:
            path = await asyncio.to_thread(
                pick_file,
                ctx.browse_title(payload, "选择文件"),
                (("文本文件", "*.txt"), ("所有文件", "*.*")),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"path": path}

    @app.post("/api/uploads")
    async def upload_text_files(payload: Dict[str, Any]):
        incoming_files = payload.get("files") or []
        try:
            metadata = ctx.project_service().upload_text_files(
                project_name=str(payload.get("project_name", "")),
                project_slug=str(payload.get("project_slug", "")),
                workflow_type=str(payload.get("workflow_type", "")),
                files=incoming_files,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        uploaded_items = metadata.uploads[-len(incoming_files):] if incoming_files else []
        return {
            "project": ctx.project_to_response(metadata),
            "items": [upload.to_dict() for upload in uploaded_items],
            "workflow_output_directory": str(
                ctx.project_service().default_export_dir(
                    metadata.project_slug,
                    metadata.workflow_type,
                )
            ),
        }

    @app.get("/api/projects")
    async def list_projects(workflow_type: str = ""):
        items = [
            ctx.project_to_response(metadata)
            for metadata in ctx.project_service().list_projects(workflow_type)
        ]
        return {"items": items}

    @app.post("/api/projects/import")
    async def import_project(payload: Dict[str, Any]):
        try:
            metadata = ctx.project_service().import_project_directory(
                source_directory=str(payload.get("path", "")),
                workflow_type=str(payload.get("workflow_type", "")),
                project_name=str(payload.get("project_name", "")),
            )
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return ctx.project_to_response(metadata)

    @app.get("/api/projects/{project_slug}")
    async def get_project(project_slug: str):
        try:
            return ctx.project_to_response(ctx.project_service().load_project(project_slug))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/api/projects/{project_slug}/repair-plan")
    async def get_project_repair_plan(project_slug: str):
        try:
            project = ctx.project_to_response(ctx.project_service().load_project(project_slug))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return {
            "project_slug": project["project_slug"],
            "reconciliation_status": project.get("reconciliation_status", ""),
            "reconciliation_warnings": project.get("reconciliation_warnings", []),
            "output_checks": project.get("output_checks", []),
            "repair_plan": project.get("repair_plan"),
        }

    @app.post("/api/projects/{project_slug}/repair")
    async def start_project_repair(project_slug: str, payload: Dict[str, Any]):
        service = ctx.project_service()
        action_id = str(payload.get("action_id", "")).strip()
        if not action_id:
            raise HTTPException(status_code=400, detail="action_id is required")
        try:
            metadata = service.load_project(project_slug)
            project = ctx.project_to_response(metadata)
            action = _find_repair_action(project.get("repair_plan"), action_id)
            _require_repair_confirmations(action, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        async def metadata_repair_runner(record, pause_signal, emit):
            emit(
                event_type="progress",
                message="开始校正项目状态",
                source_id="project_repair",
                status="INFO",
                progress_text="校正项目状态",
            )
            repaired = service.repair_project_metadata(project_slug)
            service.update_project_output(
                project_slug,
                project_name=repaired.project_name,
                custom_output_directory=repaired.custom_output_directory,
                latest_task_id=record.task_id,
                latest_task_status="success",
                summary_output_format=repaired.summary_output_format,
            )
            return TaskRunOutcome(
                status="success",
                result_summary="metadata_repaired",
                data={"action_id": action_id},
            )

        async def summary_repair_runner(record, pause_signal, emit):
            ctx.ensure_summary_scan_available(TaskType.PROJECT_REPAIR)
            settings = load_user_settings(str(app.state.user_settings_path))
            configs = load_api_configs(str(app.state.api_config_path))
            api_configs = select_api_configs(configs)
            if not api_configs:
                raise ValueError("At least one active API config is required")
            for api_config in api_configs:
                api_config["minimum_output_characters"] = settings.minimum_output_characters
            current = service.load_project(project_slug)
            output_dir, _ = service.resolve_output_selection(
                project_slug=current.project_slug,
                workflow_type=current.workflow_type,
                custom_output_directory=current.custom_output_directory,
                create=False,
            )
            request = NovelSummaryRequest(
                source_folder_path=str(output_dir),
                active_api_ids=[api_config["id"] for api_config in api_configs],
                summary_batch_size=current.summary_batch_size,
                summary_output_format=current.summary_output_format,
                big_summary_batch_size=int(payload.get("big_summary_batch_size", 5) or 5),
                super_summary_threshold=int(payload.get("super_summary_threshold", 10) or 10),
                ultimate_api_id=str(payload.get("ultimate_api_id", "")),
                use_fine_grained_flow=current.use_fine_grained_flow,
                word_counts=NovelWordCounts.from_dict(payload.get("word_counts") or {}),
                project_name=current.project_name,
                project_slug=current.project_slug,
                custom_output_directory_path=current.custom_output_directory,
                managed_output_directory_path=str(output_dir),
            )
            request.validate()
            runner = create_novel_summary_runner(request, api_configs)
            try:
                result = await runner(record, pause_signal, emit)
                status = _repair_result_status(result)
                service.update_project_output(
                    project_slug,
                    project_name=current.project_name,
                    custom_output_directory=current.custom_output_directory,
                    latest_task_id=record.task_id,
                    latest_task_status=status,
                    summary_output_format=current.summary_output_format,
                )
                return result
            except asyncio.CancelledError:
                service.update_project_output(
                    project_slug,
                    project_name=current.project_name,
                    custom_output_directory=current.custom_output_directory,
                    latest_task_id=record.task_id,
                    latest_task_status="cancelled",
                    summary_output_format=current.summary_output_format,
                )
                raise
            except Exception:
                service.update_project_output(
                    project_slug,
                    project_name=current.project_name,
                    custom_output_directory=current.custom_output_directory,
                    latest_task_id=record.task_id,
                    latest_task_status="failed",
                    summary_output_format=current.summary_output_format,
                )
                raise

        if action_id == "metadata_reconcile":
            runner = metadata_repair_runner
        elif action_id == "rerun_missing_summary_stages":
            ctx.ensure_summary_scan_available(TaskType.PROJECT_REPAIR)
            runner = summary_repair_runner
        else:
            raise HTTPException(status_code=400, detail="Unsupported repair action")

        record = await app.state.runtime.start_task(
            TaskType.PROJECT_REPAIR,
            runner,
            params_summary={
                "project_slug": project_slug,
                "action_id": action_id,
                "repair_kind": action.get("repair_kind", ""),
            },
        )
        return record.to_dict()

    @app.patch("/api/projects/{project_slug}")
    async def update_project(project_slug: str, payload: Dict[str, Any]):
        try:
            metadata = ctx.project_service().save_project_draft(
                project_slug,
                project_name=str(payload.get("project_name", "")),
                uploaded_file_ids=payload.get("uploaded_file_ids"),
                custom_output_directory=ctx.payload_custom_output(payload),
                migrate_existing_output=bool(payload.get("migrate_existing_output", False)),
                summary_output_format=str(payload.get("summary_output_format") or ""),
                summary_batch_size=int(payload.get("summary_batch_size", 0) or 0),
                use_fine_grained_flow=(
                    bool(payload["use_fine_grained_flow"])
                    if "use_fine_grained_flow" in payload
                    else None
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return ctx.project_to_response(metadata)

    @app.post("/api/projects/{project_slug}/output-migration-check")
    async def check_project_output_migration(project_slug: str, payload: Dict[str, Any]):
        try:
            return ctx.project_service().output_migration_info(
                project_slug,
                custom_output_directory=ctx.payload_custom_output(payload),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.delete("/api/projects/{project_slug}")
    async def delete_project(project_slug: str):
        try:
            result = ctx.project_service().delete_project(project_slug)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return {"ok": True, **result}

    @app.delete("/api/projects/{project_slug}/uploads")
    async def clear_project_uploads(project_slug: str):
        try:
            metadata = ctx.project_service().clear_project_uploads(project_slug)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return ctx.project_to_response(metadata)

    @app.post("/api/projects/open-directory")
    async def open_project_directory(payload: Dict[str, Any]):
        service = ctx.project_service()
        project_slug = str(payload.get("project_slug", "")).strip()
        workflow_type = str(payload.get("workflow_type", "")).strip()
        requested_output_directory = ctx.payload_custom_output(payload)
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

        path, should_return_normalized_path = ctx.normalize_user_path_value(path_str)
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
