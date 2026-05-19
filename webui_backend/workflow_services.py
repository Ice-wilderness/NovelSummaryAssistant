from __future__ import annotations

import asyncio
from typing import Callable, Dict, Iterable, List

from logic.article_summary_logic import run_article_summary_process
from logic.chapter_splitter import split_novel_into_chapter_files
from logic.custom_summary_logic import run_custom_summary_process
from logic.orchestrator import run_summarization_process

from .config_models import (
    ApiConfig,
    ArticleSummaryRequest,
    CustomSummaryRequest,
    NovelSummaryRequest,
    SplitterRequest,
)
from .config_service import resolve_api_config
from .task_runtime import TaskRecord


def select_api_configs(
    configs: Iterable[ApiConfig],
    selected_ids: Iterable[str] | None = None,
) -> List[Dict]:
    selected = set(selected_ids or [])
    active_configs = []
    for config in configs:
        if not config.is_active:
            continue
        if selected and config.id not in selected:
            continue
        resolved = resolve_api_config(config)
        active_configs.append(resolved)
    return active_configs


def find_api_config(configs: Iterable[ApiConfig], api_id: str) -> Dict:
    for config in configs:
        if config.id == api_id:
            return resolve_api_config(config)
    raise ValueError(f"Unknown api_id: {api_id}")


def make_runtime_log_callback(emit: Callable[..., None]):
    def log_callback(*args, **kwargs):
        message = kwargs.get("message")
        if message is None and args:
            message = args[0]
        source_id = (
            kwargs.get("source_id")
            or kwargs.get("api_id_for_log")
            or kwargs.get("api_id")
            or "global"
        )
        emit(
            event_type="log",
            message=str(message or ""),
            source_id=str(source_id),
            status=kwargs.get("status"),
            progress_text=kwargs.get("progress_text"),
        )

    return log_callback


def create_novel_summary_runner(request: NovelSummaryRequest, api_configs: List[Dict]):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)
        ultimate_api_id = request.ultimate_api_id or (api_configs[0]["id"] if api_configs else "")
        success = await run_summarization_process(
            novel_folder_path=request.source_folder_path,
            active_api_configs=api_configs,
            log_callback=log_callback,
            pause_event=pause_signal,
            big_summary_batch_size=request.big_summary_batch_size,
            super_summary_threshold=request.super_summary_threshold,
            ultimate_api_id=ultimate_api_id,
            word_counts=request.word_counts.to_dict(),
            use_fine_grained_flow=request.use_fine_grained_flow,
        )
        return "success" if success else "failed"

    return runner


def create_article_summary_runner(request: ArticleSummaryRequest, api_configs: List[Dict]):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)
        success = await run_article_summary_process(
            source_folder_path=request.source_folder_path,
            active_api_configs=api_configs,
            gui_log_callback=log_callback,
            gui_pause_event=pause_signal,
            gui_stop_event=None,
            word_counts=request.word_counts.to_dict(),
            selected_files=request.selected_files,
            output_subfolder=request.output_subfolder,
        )
        return "success" if success else "failed"

    return runner


def create_custom_summary_runner(request: CustomSummaryRequest, api_config: Dict):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)
        result = await run_custom_summary_process(
            selected_file_paths=request.selected_file_paths,
            user_prompt=request.user_prompt,
            api_config=api_config,
            pause_event=pause_signal,
            log_callback=log_callback,
        )
        return str(result)[:200] if result is not None else "failed"

    return runner


def create_splitter_runner(request: SplitterRequest):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)

        def run_sync():
            return split_novel_into_chapter_files(
                source_txt_file_path=request.source_txt_file_path,
                output_directory_path=request.output_directory_path,
                mode=request.mode,
                chapters_per_file=request.chapters_per_file,
                custom_pattern=request.custom_pattern,
                title_list=request.title_list,
                handle_volumes=request.handle_volumes,
                log_callback=lambda msg, level="INFO", **kwargs: log_callback(
                    message=msg,
                    status=level,
                    **kwargs,
                ),
            )

        success, count = await asyncio.to_thread(run_sync)
        return f"generated {count} files" if success else "failed"

    return runner
