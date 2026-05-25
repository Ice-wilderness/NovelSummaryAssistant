from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException

from logic.paragraph_index import build_chapter_paragraph_index, extract_paragraph_context

from ..config_service import load_api_configs, load_user_settings
from ..task_runtime import TaskType
from ..trigger_models import TriggerScanConfig
from ..workflow_services import create_trigger_scan_runner, select_api_configs
from .context import RouteContext


def _record_response(record) -> Dict[str, Any]:
    return record.to_dict()


def register_trigger_scan_routes(ctx: RouteContext) -> None:
    app = ctx.app

    @app.post("/api/trigger-scan/precheck")
    async def precheck_trigger_scan(payload: Dict[str, Any]):
        try:
            request, profile, _metadata, _output_dir = ctx.resolve_trigger_scan_request(
                payload,
                create_output=False,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return ctx.trigger_scan_validation_payload(request, profile)

    @app.get("/api/trigger-scan/projects/{project_slug}/config")
    async def get_trigger_scan_config(project_slug: str):
        try:
            metadata = ctx.project_service().load_project(project_slug)
            output_dir, _effective = ctx.project_service().resolve_output_selection(
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
            metadata = ctx.project_service().load_project(project_slug)
            output_dir, _effective = ctx.project_service().resolve_output_selection(
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
        ctx.ensure_summary_scan_available(TaskType.TRIGGER_SCAN)
        try:
            request, profile, _metadata, _output_dir = ctx.resolve_trigger_scan_request(
                payload,
                create_output=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        validation = ctx.trigger_scan_validation_payload(request, profile)
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
            verification_api_config["minimum_output_characters"] = (
                request.scan_config.minimum_output_characters
            )

        runner = create_trigger_scan_runner(
            request,
            profile,
            scan_api_configs,
            verification_api_config=verification_api_config,
        )
        record = await app.state.runtime.start_task(
            TaskType.TRIGGER_SCAN,
            ctx.wrap_runner_with_project_status(runner, request),
            params_summary={
                **request.__dict__,
                "scan_config": request.scan_config.to_dict(),
            },
        )
        if request.project_slug:
            ctx.project_service().update_project_output(
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
            store, _output_dir, _metadata = ctx.trigger_report_store_for_project(project_slug)
            return {"items": [entry.to_dict() for entry in store.list_reports()]}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.get("/api/trigger-scan/projects/{project_slug}/reports/{report_id}")
    async def get_trigger_scan_report(project_slug: str, report_id: str):
        try:
            store, _output_dir, _metadata = ctx.trigger_report_store_for_project(project_slug)
            return store.load_report(report_id).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.delete("/api/trigger-scan/projects/{project_slug}/reports/{report_id}")
    async def delete_trigger_scan_report(project_slug: str, report_id: str):
        try:
            store, _output_dir, _metadata = ctx.trigger_report_store_for_project(
                project_slug,
                create=True,
            )
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
            store, _output_dir, _metadata = ctx.trigger_report_store_for_project(
                project_slug,
                create=True,
            )
            finding = store.update_finding_review(
                report_id,
                finding_id,
                review_status=payload.get("review_status"),
                user_note=payload.get("user_note"),
            )
            return finding.to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get(
        "/api/trigger-scan/projects/{project_slug}/reports/{report_id}/findings/{finding_id}/context"
    )
    async def get_trigger_scan_finding_context(
        project_slug: str,
        report_id: str,
        finding_id: str,
        before: int = 1,
        after: int = 1,
    ):
        try:
            store, output_dir, _metadata = ctx.trigger_report_store_for_project(project_slug)
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
            store, _output_dir, _metadata = ctx.trigger_report_store_for_project(
                project_slug,
                create=True,
            )
            if export_format == "json":
                path = store.export_report_json(report_id)
            elif export_format in {"md", "markdown"}:
                path = store.export_report_markdown(report_id)
            else:
                raise ValueError("format must be one of: md, json")
            return {"path": str(path), "format": export_format}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
