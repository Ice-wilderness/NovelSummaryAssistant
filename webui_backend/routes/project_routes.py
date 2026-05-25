from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import HTTPException

from ..local_picker import pick_directory, pick_file
from .context import RouteContext


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
