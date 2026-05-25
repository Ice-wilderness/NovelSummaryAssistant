from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List

from fastapi import FastAPI

from webui_backend.project_workspace import UploadedFileRef
from webui_backend.task_runtime import TaskType


@dataclass(frozen=True)
class RouteContext:
    app: FastAPI
    project_service: Callable[[], Any]
    trigger_profile_service: Callable[[], Any]
    pattern_config_service: Callable[[], Any]
    ensure_summary_scan_available: Callable[[TaskType], None]
    project_to_response: Callable[[Any], Dict[str, Any]]
    resolve_project_uploads: Callable[
        [Dict[str, Any], TaskType],
        tuple[str, str, str, Path, List[UploadedFileRef]],
    ]
    add_project_fields: Callable[[Any, Dict[str, Any], Path | None], None]
    wrap_runner_with_project_status: Callable[[Any, Any], Any]
    resolve_trigger_scan_request: Callable[[Dict[str, Any]], Any]
    trigger_scan_validation_payload: Callable[[Any, Any], Dict[str, Any]]
    trigger_report_store_for_project: Callable[..., Any]
