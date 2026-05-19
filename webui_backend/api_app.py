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
from .local_picker import pick_directory, pick_file
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


def _record_response(record) -> Dict[str, Any]:
    return record.to_dict()


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


def _browse_filetypes(payload: Dict[str, Any] | None) -> List[tuple[str, str]] | None:
    raw_filetypes = (payload or {}).get("filetypes")
    if not isinstance(raw_filetypes, list):
        return None
    filetypes: List[tuple[str, str]] = []
    for item in raw_filetypes:
        if isinstance(item, list) and len(item) >= 2:
            filetypes.append((str(item[0]), str(item[1])))
    return filetypes or None


def create_app(
    *,
    api_config_path: str | Path | None = None,
    prompt_cache_dir: str | Path | None = None,
    frontend_dist_dir: str | Path | None = None,
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

    @app.post("/api/browse/file")
    async def browse_file(payload: Dict[str, Any] | None = None):
        try:
            path = await asyncio.to_thread(
                pick_file,
                _browse_title(payload, "选择文件"),
                _browse_filetypes(payload),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"path": path}

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
            word_counts=NovelWordCounts.from_dict(payload.get("word_counts") or {}),
        )
        return await _start_task(TaskType.NOVEL_SUMMARY, request)

    @app.post("/api/tasks/article")
    async def start_article_task(payload: Dict[str, Any]):
        request = ArticleSummaryRequest(
            source_folder_path=str(payload.get("source_folder_path", "")),
            selected_files=list(payload.get("selected_files", [])),
            output_subfolder=str(payload.get("output_subfolder", "")),
            word_counts=ArticleWordCounts.from_dict(payload.get("word_counts") or {}),
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
