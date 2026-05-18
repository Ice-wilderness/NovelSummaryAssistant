from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from logic.llm_api import fetch_available_models

from .config_models import (
    ApiConfig,
    ArticleSummaryRequest,
    CustomSummaryRequest,
    NovelSummaryRequest,
    SplitterRequest,
)
from .config_service import (
    load_api_configs,
    load_prompt_templates,
    prepare_api_configs_for_save,
    public_api_configs,
    reset_prompt_template,
    resolve_api_config,
    save_api_configs,
    save_prompt_template,
)
from .file_services import ensure_prompt_cache_dir, get_project_root
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


def _record_response(record) -> Dict[str, Any]:
    return record.to_dict()


def _get_prompt_template(cache_dir: Path, prompt_key: str):
    for template in load_prompt_templates(str(cache_dir)):
        if template.key == prompt_key:
            return template
    raise HTTPException(status_code=404, detail=f"Unknown prompt key: {prompt_key}")


def create_app(
    *,
    api_config_path: str | Path | None = None,
    prompt_cache_dir: str | Path | None = None,
    runtime: TaskRuntime | None = None,
) -> FastAPI:
    app = FastAPI(title="NovelSummaryAssistant WebUI API")
    app.state.runtime = runtime or TaskRuntime()
    app.state.api_config_path = Path(api_config_path) if api_config_path else _default_api_config_path()
    app.state.prompt_cache_dir = (
        Path(prompt_cache_dir) if prompt_cache_dir else ensure_prompt_cache_dir()
    )

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
        configs = prepare_api_configs_for_save(payload, existing_configs)
        save_api_configs(str(app.state.api_config_path), configs)
        return {"items": public_api_configs(configs)}

    @app.get("/api/prompts")
    async def get_prompts():
        templates = load_prompt_templates(str(app.state.prompt_cache_dir))
        return {"items": [template.to_dict() for template in templates]}

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

    @app.post("/api/models")
    async def get_models(payload: Dict[str, Any]):
        config = ApiConfig.from_dict(payload)
        resolved = resolve_api_config(config)
        if not resolved.get("url") or not resolved.get("key"):
            raise HTTPException(status_code=400, detail="API url and key are required")
        models, error = await fetch_available_models(resolved["url"], resolved["key"])
        if error:
            raise HTTPException(status_code=400, detail=error)
        return {"items": models}

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
            runner,
            params_summary=request.__dict__,
        )
        return _record_response(record)

    @app.post("/api/tasks/novel")
    async def start_novel_task(payload: Dict[str, Any]):
        request = NovelSummaryRequest(
            source_folder_path=str(payload.get("source_folder_path", "")),
            active_api_ids=list(payload.get("active_api_ids", [])),
            big_summary_batch_size=payload.get("big_summary_batch_size", 5),
            super_summary_threshold=payload.get("super_summary_threshold", 5),
            ultimate_api_id=str(payload.get("ultimate_api_id", "")),
            use_fine_grained_flow=bool(payload.get("use_fine_grained_flow", False)),
        )
        return await _start_task(TaskType.NOVEL_SUMMARY, request)

    @app.post("/api/tasks/article")
    async def start_article_task(payload: Dict[str, Any]):
        request = ArticleSummaryRequest(
            source_folder_path=str(payload.get("source_folder_path", "")),
            selected_files=list(payload.get("selected_files", [])),
            output_subfolder=str(payload.get("output_subfolder", "")),
        )
        return await _start_task(TaskType.ARTICLE_SUMMARY, request)

    @app.post("/api/tasks/custom")
    async def start_custom_task(payload: Dict[str, Any]):
        request = CustomSummaryRequest(
            selected_file_paths=list(payload.get("selected_file_paths", [])),
            user_prompt=str(payload.get("user_prompt", "")),
            api_id=str(payload.get("api_id", "")),
        )
        try:
            request.validate()
            api_config = find_api_config(load_api_configs(str(app.state.api_config_path)), request.api_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        record = await app.state.runtime.start_task(
            TaskType.CUSTOM_SUMMARY,
            create_custom_summary_runner(request, api_config),
            params_summary=request.__dict__,
        )
        return _record_response(record)

    @app.post("/api/tasks/splitter")
    async def start_splitter_task(payload: Dict[str, Any]):
        request = SplitterRequest(
            source_txt_file_path=str(payload.get("source_txt_file_path", "")),
            output_directory_path=str(payload.get("output_directory_path", "")),
            mode=str(payload.get("mode", "default")),
            chapters_per_file=payload.get("chapters_per_file", 1),
            custom_pattern=str(payload.get("custom_pattern", "")),
            title_list=list(payload.get("title_list", [])),
            handle_volumes=bool(payload.get("handle_volumes", True)),
        )
        return await _start_task(TaskType.CHAPTER_SPLIT, request)

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

    return app


app = create_app()
