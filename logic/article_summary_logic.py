# logic/article_summary_logic.py
"""
Contains the core processing logic for the article summarization task.
This is a simplified, two-step version of the novel summarization process.
"""
import os
import glob
import traceback
import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from logic import utils
from logic.llm_api import get_llm_summary_with_config
from logic.utils import load_all_prompts_for_run, log_message

# --- Constants for subdirectories ---
USER_FACING_ARTICLE_SECTION_SUBDIR = "1_文章段落总结"
USER_FACING_ARTICLE_FINAL_SUBDIR = "2_文章最终总结"
# State file for this specific mode
ARTICLE_STATE_FILENAME = "article_summary_state.json"


@dataclass
class ArticleSummaryResult:
    status: str
    result_summary: str
    final_output_path: str = ""
    warnings: List[str] = field(default_factory=list)
    failed_sections: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def __bool__(self) -> bool:
        return self.status != "failed"

    @property
    def data(self) -> Dict[str, Any]:
        return {
            "final_output_path": self.final_output_path,
            "failed_sections": list(self.failed_sections),
        }


def _article_success(final_output_path: str = "") -> ArticleSummaryResult:
    return ArticleSummaryResult(
        status="success",
        result_summary="success",
        final_output_path=final_output_path,
    )


def _article_failed(message: str, failed_sections: Optional[List[Dict[str, Any]]] = None) -> ArticleSummaryResult:
    return ArticleSummaryResult(
        status="failed",
        result_summary="failed",
        failed_sections=list(failed_sections or []),
        error=message,
    )


def _article_partial(
    final_output_path: str,
    failed_sections: List[Dict[str, Any]],
) -> ArticleSummaryResult:
    failed_names = [str(item.get("filename") or item.get("source_file") or "") for item in failed_sections]
    warning = "部分文章段落总结失败，最终总结仅基于成功段落生成，结果可能不完整。"
    if failed_names:
        warning = f"{warning}失败段落：{', '.join(name for name in failed_names if name)}"
    return ArticleSummaryResult(
        status="partial_failed",
        result_summary="partial_failed",
        final_output_path=final_output_path,
        warnings=[warning],
        failed_sections=list(failed_sections),
        error=warning,
    )


def _load_state_file(state_filepath):
    if not os.path.exists(state_filepath):
        return {}
    try:
        with open(state_filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state_file(state_filepath, state):
    os.makedirs(os.path.dirname(state_filepath), exist_ok=True)
    temp_filepath = state_filepath + ".tmp"
    with open(temp_filepath, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=4)
    os.replace(temp_filepath, state_filepath)


async def _load_article_state(state_filepath):
    return await asyncio.to_thread(_load_state_file, state_filepath)


async def _save_article_state(state_filepath, state):
    await asyncio.to_thread(_save_state_file, state_filepath, state)


def _stop_requested(stop_event):
    return bool(stop_event and getattr(stop_event, "is_set", lambda: False)())


async def run_article_summary_process(
    source_folder_path,
    active_api_configs,
    gui_log_callback,
    gui_pause_event,
    gui_stop_event,
    word_counts,
    selected_files=None,
    output_subfolder=""
):
    """
    The main backend process for summarizing non-fiction articles.
    This async entry point can be scheduled directly by the task runtime.
    """
    return await _actual_article_summary_process(
        source_folder_path, active_api_configs, gui_log_callback,
        gui_pause_event, gui_stop_event, word_counts, selected_files, output_subfolder
    )


def run_article_summary_process_sync(
    source_folder_path,
    active_api_configs,
    gui_log_callback,
    gui_pause_event,
    gui_stop_event,
    word_counts,
    selected_files=None,
    output_subfolder=""
):
    """Synchronous compatibility wrapper for non-async callers."""
    return asyncio.run(
        run_article_summary_process(
            source_folder_path, active_api_configs, gui_log_callback,
            gui_pause_event, gui_stop_event, word_counts, selected_files, output_subfolder
        )
    )


def _normalize_selected_article_files(source_folder_path, selected_files):
    if not selected_files:
        return None
    normalized = set()
    source_abs = os.path.abspath(source_folder_path)
    for selected in selected_files:
        if not selected:
            continue
        selected_path = selected if os.path.isabs(selected) else os.path.join(source_abs, selected)
        normalized.add(os.path.normcase(os.path.abspath(selected_path)))
    return normalized


async def _actual_article_summary_process(
    source_folder_path,
    active_api_configs,
    log_callback,
    pause_event,
    stop_event,
    word_counts,
    selected_files=None,
    output_subfolder=""
):
    """
    The actual async implementation of the article summarization logic.
    """
    try:
        log_message(log_callback, "--- 文章总结任务启动 ---")

        # --- Setup ---
        output_root = source_folder_path
        if output_subfolder:
            output_root = os.path.join(source_folder_path, output_subfolder)
            os.makedirs(output_root, exist_ok=True)
        cache_dir = os.path.join(output_root, ".summarizer_cache")
        section_summary_dir = os.path.join(cache_dir, USER_FACING_ARTICLE_SECTION_SUBDIR)
        final_summary_dir = os.path.join(cache_dir, USER_FACING_ARTICLE_FINAL_SUBDIR)
        os.makedirs(section_summary_dir, exist_ok=True)
        os.makedirs(final_summary_dir, exist_ok=True)

        state_filepath = os.path.join(cache_dir, ARTICLE_STATE_FILENAME)
        state = await _load_article_state(state_filepath)
        
        if not active_api_configs:
            message = "错误：没有活动的API配置。请至少启用一个API。"
            log_message(log_callback, message)
            return _article_failed(message)
        api_config = active_api_configs[0]

        all_files = sorted(
            glob.glob(os.path.join(source_folder_path, "*.txt")),
            key=lambda f: utils.get_chapter_range_from_filename(f)[0]
        )
        selected_file_set = _normalize_selected_article_files(source_folder_path, selected_files)
        if selected_file_set is not None:
            all_files = [
                filepath for filepath in all_files
                if os.path.normcase(os.path.abspath(filepath)) in selected_file_set
            ]
        if not all_files:
            message = "错误：在源文件夹中未找到任何 .txt 文件。"
            log_message(log_callback, message)
            return _article_failed(message)

        log_message(log_callback, f"找到 {len(all_files)} 个待处理的文件。")
        prompts = load_all_prompts_for_run()

        # --- Stage 1: Section Summaries ---
        log_message(log_callback, "\n--- 阶段 1: 生成段落总结 ---")
        processed_sections = state.get('processed_sections', [])
        failed_sections = []
        for filepath in all_files:
            if _stop_requested(stop_event):
                message = "任务被用户中止。"
                log_message(log_callback, message)
                return _article_failed(message, failed_sections)
            await utils.check_pause_async(pause_event)
            filename = os.path.basename(filepath)
            output_filename = f"summary_{filename}"
            output_filepath = os.path.join(section_summary_dir, output_filename)

            if output_filepath in processed_sections and os.path.exists(output_filepath):
                log_message(log_callback, f"已跳过 (已处理): {filename}")
                continue

            log_message(log_callback, f"正在处理段落: {filename}")
            content = utils.read_file_content_robustly(filepath)
            
            start_time = time.time()
            try:
                summary_text = await get_llm_summary_with_config(
                    api_config,
                    prompts['prompt_article_section'],
                    {
                        'current_chunk_text': content,
                        'filename_for_context': filename,
                    },
                    log_callback,
                    task_info={
                        'novel_folder_path': output_root,
                        'stage': 'article_section',
                        'source_file': filepath,
                        'source_char_count': len(content),
                        'progress_text': f"文章段落 {filename}",
                    },
                    section_word_count=word_counts.get('section', '3000-4000')
                )
            except Exception as e:
                failed_section = {
                    "filename": filename,
                    "source_file": filepath,
                    "stage": "article_section",
                    "error": str(e),
                }
                failed_sections.append(failed_section)
                state["failed_sections"] = failed_sections
                await _save_article_state(state_filepath, state)
                log_message(log_callback, f"处理 {filename} 时出错，跳过此文件。错误: {e}")
                continue
            duration = time.time() - start_time
            char_count = len(summary_text)

            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(summary_text)
            log_message(log_callback, f"已保存段落总结: {output_filename} (耗时: {duration:.2f}s, 字数: {char_count})")
            
            processed_sections.append(output_filepath)
            state['processed_sections'] = processed_sections
            await _save_article_state(state_filepath, state)

        # --- Stage 2: Final Summary ---
        log_message(log_callback, "\n--- 阶段 2: 生成最终总结 ---")
        final_output_path = os.path.join(final_summary_dir, "最终总结_全文.txt")
        if not state.get('final_summary_complete', False):
            if _stop_requested(stop_event):
                message = "任务被用户中止。"
                log_message(log_callback, message)
                return _article_failed(message, failed_sections)
            await utils.check_pause_async(pause_event)
            all_section_summaries = []
            for summary_file in os.listdir(section_summary_dir):
                full_path = os.path.join(section_summary_dir, summary_file)
                all_section_summaries.append(utils.read_file_content_robustly(full_path))
            
            if not all_section_summaries:
                message = "没有找到任何段落总结，无法生成最终总结。"
                log_message(log_callback, message)
                state["failed_sections"] = failed_sections
                state["partial_warnings"] = []
                await _save_article_state(state_filepath, state)
                return _article_failed(message, failed_sections)

            concatenated_summaries = "\n\n---\n\n".join(all_section_summaries)
            
            start_time = time.time()
            try:
                final_summary_text = await get_llm_summary_with_config(
                    api_config,
                    prompts['prompt_article_final'],
                    {
                        'concatenated_section_summaries': concatenated_summaries,
                    },
                    log_callback,
                    task_info={
                        'novel_folder_path': output_root,
                        'stage': 'article_final',
                        'source_files': list(os.listdir(section_summary_dir)),
                        'source_char_count': len(concatenated_summaries),
                        'progress_text': "文章最终总结",
                    },
                    final_word_count=word_counts.get('final', '8000-10000')
                )
            except Exception as e:
                message = f"生成最终总结时出错: {e}"
                log_message(log_callback, message)
                state["failed_sections"] = failed_sections
                state["partial_warnings"] = []
                await _save_article_state(state_filepath, state)
                return _article_failed(message, failed_sections)
            duration = time.time() - start_time
            char_count = len(final_summary_text)

            with open(final_output_path, 'w', encoding='utf-8') as f:
                f.write(final_summary_text)
            
            log_message(log_callback, f"已保存最终总结: {os.path.basename(final_output_path)} (耗时: {duration:.2f}s, 字数: {char_count})")
            state['final_summary_complete'] = True
            state["failed_sections"] = failed_sections
            partial_result = _article_partial(final_output_path, failed_sections) if failed_sections else None
            state["partial_warnings"] = partial_result.warnings if partial_result else []
            await _save_article_state(state_filepath, state)
        else:
            log_message(log_callback, "已跳过 (已完成): 最终总结")
            failed_sections = list(state.get("failed_sections", []))

        log_message(log_callback, "\n--- 文章总结任务成功完成 ---")
        if failed_sections:
            return _article_partial(final_output_path, failed_sections)
        return _article_success(final_output_path)

    except asyncio.CancelledError:
        log_message(log_callback, "任务被用户取消。")
        raise
    except InterruptedError:
        message = "任务被用户中止。"
        log_message(log_callback, message)
        return _article_failed(message)
    except Exception as e:
        tb_str = traceback.format_exc()
        user_msg = f"文章总结过程中发生严重错误: {e}"
        log_message(log_callback, user_msg, traceback_info=tb_str)
        return _article_failed(user_msg)
