from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from logic.chapter_splitter import split_novel_into_chapter_files

from ..config_models import (
    ArticleSummaryRequest,
    ArticleWordCounts,
    ChapterPreviewItem,
    ChapterPreviewRequest,
    CustomSummaryRequest,
    NovelSummaryRequest,
    NovelWordCounts,
    SplitPreviewResult,
    SplitterRequest,
)
from ..config_service import load_api_configs, load_user_settings
from ..task_runtime import TaskType
from ..workflow_services import (
    create_article_summary_runner,
    create_custom_summary_runner,
    create_novel_summary_runner,
    create_splitter_runner,
    find_api_config,
    select_api_configs,
)
from .context import RouteContext


def _record_response(record) -> Dict[str, Any]:
    return record.to_dict()


def register_summary_task_routes(ctx: RouteContext) -> None:
    app = ctx.app

    async def _start_task(task_type: TaskType, request):
        ctx.ensure_summary_scan_available(task_type)
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
            ctx.wrap_runner_with_project_status(runner, request),
            params_summary=request.__dict__,
        )
        if getattr(request, "project_slug", ""):
            ctx.project_service().update_project_output(
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
        project_slug_for_start = ctx.payload_project_slug(payload)
        project_metadata_for_start = None
        if project_slug_for_start:
            try:
                metadata = ctx.project_service().load_project(project_slug_for_start)
                project_metadata_for_start = metadata
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        if ctx.payload_file_ids(payload):
            try:
                _, _, _, output_dir, uploads = ctx.resolve_project_uploads(
                    payload,
                    TaskType.NOVEL_SUMMARY,
                )
                ctx.project_service().prepare_copied_inputs(output_dir=output_dir, uploads=uploads)
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
        ctx.add_project_fields(request, payload, output_dir)
        return await _start_task(task_type, request)

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
        if ctx.payload_file_ids(payload):
            try:
                _, _, _, output_dir, uploads = ctx.resolve_project_uploads(
                    payload,
                    TaskType.ARTICLE_SUMMARY,
                )
                selected_files = ctx.project_service().prepare_copied_inputs(
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
        ctx.add_project_fields(request, payload, output_dir)
        return await _start_task(TaskType.ARTICLE_SUMMARY, request)

    @app.post("/api/tasks/custom")
    async def start_custom_task(payload: Dict[str, Any]):
        selected_file_paths = list(payload.get("selected_file_paths", []))
        output_dir: Path | None = None
        if ctx.payload_file_ids(payload):
            try:
                _, _, _, output_dir, uploads = ctx.resolve_project_uploads(
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
        ctx.add_project_fields(request, payload, output_dir)
        try:
            request.validate()
            api_config = find_api_config(load_api_configs(str(app.state.api_config_path)), request.api_id)
            settings = load_user_settings(str(app.state.user_settings_path))
            api_config["minimum_output_characters"] = settings.minimum_output_characters
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        record = await app.state.runtime.start_task(
            TaskType.CUSTOM_SUMMARY,
            ctx.wrap_runner_with_project_status(
                create_custom_summary_runner(request, api_config),
                request,
            ),
            params_summary=request.__dict__,
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

    @app.post("/api/chapters/preview-split")
    async def preview_chapter_split(payload: Dict[str, Any]):
        file_content = str(payload.get("file_content", ""))

        upload_ids = ctx.payload_file_ids(payload)
        if upload_ids and not file_content:
            try:
                _, _, _, _, uploads = ctx.resolve_project_uploads(
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
                pattern_config = ctx.pattern_config_service().get(request.pattern_config_id)
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

        custom_pattern = str(payload.get("custom_pattern", ""))
        pattern_config_id = str(payload.get("pattern_config_id", ""))
        pattern_config = None
        if mode == "regex" and pattern_config_id:
            try:
                pattern_config = ctx.pattern_config_service().get(pattern_config_id)
                if pattern_config.regex_mode == "simple":
                    custom_pattern = pattern_config.pattern
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

        title_list = list(payload.get("title_list", []))

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
        context = str(payload.get("context", "chapter_split"))
        source_txt_file_path = str(payload.get("source_txt_file_path", ""))
        output_directory_path = str(payload.get("output_directory_path", ""))
        output_dir: Path | None = None

        file_content = str(payload.get("file_content", ""))
        if context == "novel_summary" and file_content:
            project_slug = ctx.payload_project_slug(payload)
            project_name = ctx.payload_project_name(payload)
            if not project_slug:
                raise HTTPException(status_code=400, detail="novel_summary 上下文需要 project_slug")

            try:
                ctx.project_service().load_project(project_slug)
            except ValueError:
                ctx.project_service().ensure_project(
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
                    pattern_config = ctx.pattern_config_service().get(pattern_config_id)
                    if pattern_config.regex_mode == "simple":
                        custom_pattern = pattern_config.pattern
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc))

            tmp = Path(tempfile.gettempdir()) / f"nv_split_{int(time.time() * 1000)}.txt"
            try:
                tmp.write_text(file_content, encoding="utf-8")
                metadata = ctx.project_service().split_and_ingest_source_file(
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
            return ctx.project_to_response(metadata)

        if ctx.payload_file_ids(payload):
            try:
                _, _, _, output_dir, uploads = ctx.resolve_project_uploads(
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
        ctx.add_project_fields(request, payload, output_dir)
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
            if record and ctx.is_terminal_status(record.status.value):
                terminal_event = next(
                    (
                        event
                        for event in reversed(record.events)
                        if ctx.is_terminal_status(event.status)
                    ),
                    None,
                )
                if terminal_event:
                    yield f"data: {json.dumps(terminal_event.to_dict(), ensure_ascii=False)}\n\n"
                return
            while True:
                event = await app.state.runtime.next_event(task_id)
                yield f"data: {json.dumps(event.to_dict(), ensure_ascii=False)}\n\n"
                if ctx.is_terminal_status(event.status):
                    return

        return StreamingResponse(stream(), media_type="text/event-stream")
