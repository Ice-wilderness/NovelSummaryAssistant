# logic/article_summary_logic.py
"""
Contains the core processing logic for the article summarization task.
This is a simplified, two-step version of the novel summarization process.
"""
import os
import glob
import traceback
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from logic import state_manager
from logic import utils
from logic.llm_api import get_llm_summary_with_config, APIPermanentError
from logic.utils import load_all_prompts_for_run, log_message, check_pause_async, read_file_content_robustly

# --- Constants for subdirectories ---
USER_FACING_ARTICLE_SECTION_SUBDIR = "1_文章段落总结"
USER_FACING_ARTICLE_FINAL_SUBDIR = "2_文章最终总结"
# State file for this specific mode
ARTICLE_STATE_FILENAME = "article_summary_state.json"

def run_article_summary_process(
    source_folder_path,
    active_api_configs,
    gui_log_callback,
    gui_pause_event,
    gui_stop_event,
    word_counts
):
    """
    The main backend process for summarizing non-fiction articles.
    This is the synchronous entry point that runs the async logic.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(
            _actual_article_summary_process(
                source_folder_path, active_api_configs, gui_log_callback,
                gui_pause_event, gui_stop_event, word_counts
            )
        )
    finally:
        loop.close()


async def _actual_article_summary_process(
    source_folder_path,
    active_api_configs,
    log_callback,
    pause_event,
    stop_event,
    word_counts
):
    """
    The actual async implementation of the article summarization logic.
    """
    try:
        log_message(log_callback, "--- 文章总结任务启动 ---")

        # --- Setup ---
        cache_dir = os.path.join(source_folder_path, ".summarizer_cache")
        section_summary_dir = os.path.join(cache_dir, USER_FACING_ARTICLE_SECTION_SUBDIR)
        final_summary_dir = os.path.join(cache_dir, USER_FACING_ARTICLE_FINAL_SUBDIR)
        os.makedirs(section_summary_dir, exist_ok=True)
        os.makedirs(final_summary_dir, exist_ok=True)

        state_filepath = os.path.join(cache_dir, ARTICLE_STATE_FILENAME)
        state = await state_manager.load_state_async(state_filepath) or {}
        
        api_config = active_api_configs[0]

        all_files = sorted(
            glob.glob(os.path.join(source_folder_path, "*.txt")),
            key=lambda f: utils.get_chapter_range_from_filename(f)[0]
        )
        if not all_files:
            log_message(log_callback, "错误：在源文件夹中未找到任何 .txt 文件。")
            return False

        log_message(log_callback, f"找到 {len(all_files)} 个待处理的文件。")
        prompts = load_all_prompts_for_run()

        # --- Stage 1: Section Summaries ---
        log_message(log_callback, "\n--- 阶段 1: 生成段落总结 ---")
        processed_sections = state.get('processed_sections', [])
        for filepath in all_files:
            await utils.check_pause_async(pause_event)
            filename = os.path.basename(filepath)
            output_filename = f"summary_{filename}"
            output_filepath = os.path.join(section_summary_dir, output_filename)

            if output_filepath in processed_sections and os.path.exists(output_filepath):
                log_message(log_callback, f"已跳过 (已处理): {filename}")
                continue

            log_message(log_callback, f"正在处理段落: {filename}")
            content = utils.read_file_content_robustly(filepath)
            
            summary_data, error = await get_llm_summary_with_config(
                action_description=f"段落总结: {filename}",
                llm_prompt_func=lambda p, *args: p['prompt_article_section']['text'].format(
                    current_chunk_text=args[0],
                    section_word_count=args[1],
                    filename_for_context=args[2]
                ),
                api_config_dict=api_config,
                prompt_configs=prompts,
                log_callback=log_callback,
                pause_event=pause_event,
                prompt_args=[
                    content,
                    word_counts.get('section', '3000-4000'),
                    filename
                ],
                progress_text=f"段落: {filename}"
            )

            if error:
                 log_message(log_callback, f"处理 {filename} 时出错，跳过此文件。错误: {error}")
                 continue

            summary_text, duration, char_count = summary_data
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(summary_text)
            log_message(log_callback, f"已保存段落总结: {output_filename} (耗时: {duration:.2f}s, 字数: {char_count})")
            
            processed_sections.append(output_filepath)
            state['processed_sections'] = processed_sections
            await state_manager.save_state_async(state_filepath, state)

        # --- Stage 2: Final Summary ---
        log_message(log_callback, "\n--- 阶段 2: 生成最终总结 ---")
        if not state.get('final_summary_complete', False):
            await utils.check_pause_async(pause_event)
            all_section_summaries = []
            for summary_file in os.listdir(section_summary_dir):
                full_path = os.path.join(section_summary_dir, summary_file)
                all_section_summaries.append(utils.read_file_content_robustly(full_path))
            
            if not all_section_summaries:
                log_message(log_callback, "没有找到任何段落总结，无法生成最终总结。")
                return False

            concatenated_summaries = "\n\n---\n\n".join(all_section_summaries)
            
            final_summary_data, error = await get_llm_summary_with_config(
                action_description="最终总结",
                llm_prompt_func=lambda p, *args: p['prompt_article_final']['text'].format(
                    concatenated_section_summaries=args[0],
                    final_word_count=args[1]
                ),
                api_config_dict=api_config,
                prompt_configs=prompts,
                log_callback=log_callback,
                pause_event=pause_event,
                prompt_args=[
                    concatenated_summaries,
                    word_counts.get('final', '8000-10000')
                ],
                progress_text="生成最终总结"
            )

            if error:
                log_message(log_callback, f"生成最终总结时出错: {error}")
                return False

            final_summary_text, duration, char_count = final_summary_data
            final_output_path = os.path.join(final_summary_dir, "最终总结_全文.txt")
            with open(final_output_path, 'w', encoding='utf-8') as f:
                f.write(final_summary_text)
            
            log_message(log_callback, f"已保存最终总结: {os.path.basename(final_output_path)} (耗时: {duration:.2f}s, 字数: {char_count})")
            state['final_summary_complete'] = True
            await state_manager.save_state_async(state_filepath, state)
        else:
            log_message(log_callback, "已跳过 (已完成): 最终总结")

        log_message(log_callback, "\n--- 文章总结任务成功完成 ---")
        return True

    except InterruptedError:
        log_message(log_callback, "任务被用户中止。")
        return False
    except Exception as e:
        tb_str = traceback.format_exc()
        user_msg = f"文章总结过程中发生严重错误: {e}"
        log_message(log_callback, user_msg, traceback_info=tb_str)
        return False 
