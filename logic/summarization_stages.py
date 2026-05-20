"""
This module contains the logic for the different stages of the summarization process.
"""
import os
import traceback
import asyncio
import aiofiles
from typing import Dict, List, Callable, Tuple

from . import state_manager as sm
from logic.llm_api import get_llm_summary_with_config
from logic.utils import (
    _distribute_chapters_sequentially, _distribute_batches_sequentially,
    log_message, check_pause_async,
    extract_character_info_from_summary, extract_summary_content, get_summarizer_cache_dir,
    sanitize_api_name, get_big_summary_sort_key,
    get_super_ultimate_summary_sort_key
)
from logic.prompts import (
    USER_FACING_SMALL_PLOT_SUBDIR, USER_FACING_SMALL_CHAR_SUBDIR,
    USER_FACING_BIG_PLOT_SUBDIR, USER_FACING_BIG_CHAR_SUBDIR,
    USER_FACING_SUPER_PLOT_P1_SUBDIR, USER_FACING_SUPER_PLOT_P2_SUBDIR,
    USER_FACING_SUPER_CHAR_P1_SUBDIR, USER_FACING_SUPER_CHAR_P2_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P1_SUBDIR, USER_FACING_ULTIMATE_PLOT_P2_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P1_SUBDIR, USER_FACING_ULTIMATE_CHAR_P2_SUBDIR,
    FINAL_SUMMARY_DIR
)
from logic import utils

def _distribute_batches_by_assignment(
    batches: List[Tuple[str, List[str]]],
    assignments: Dict[str, int]
) -> Dict[str, List[Tuple[str, List[str]]]]:
    """根据明确的分配将批次分发给API。"""
    distribution = {api_id: [] for api_id in assignments}
    batches_iterator = iter(batches)
    for api_id, count in assignments.items():
        if count > 0:
            assigned_for_this_api = []
            try:
                for _ in range(count):
                    assigned_for_this_api.append(next(batches_iterator))
                distribution[api_id] = assigned_for_this_api
            except StopIteration:
                distribution[api_id] = assigned_for_this_api
                break
    return distribution

def _path_starts_with_any_batch_name(filepath: str, batch_names: List[str]) -> bool:
    stem = os.path.splitext(os.path.basename(filepath))[0]
    return any(stem.startswith(f"{batch_name}_") for batch_name in batch_names)

def _select_big_summary_files_for_api(
    cache_dir: str,
    source_subdir: str,
    sane_api_name: str,
    state_manager: sm.StateManager,
    api_id: str,
    sub_stage_name: str,
    big_summary_batch_size: int,
    log_callback: Callable,
    api_display_name: str,
) -> List[str]:
    big_summary_dir = os.path.join(cache_dir, source_subdir)
    if not os.path.isdir(big_summary_dir):
        return []

    all_files = [
        os.path.join(big_summary_dir, filename)
        for filename in os.listdir(big_summary_dir)
        if filename.endswith(".txt")
    ]
    api_suffix = f"_{sane_api_name}.txt"
    files_for_api = [filepath for filepath in all_files if filepath.endswith(api_suffix)]
    if files_for_api:
        files_for_api.sort(key=get_big_summary_sort_key)
        return files_for_api

    completed_batches = state_manager.get_completed_big_summary_batches_for_api(
        api_id,
        sub_stage_name,
        big_summary_batch_size,
    )
    if not completed_batches:
        completed_batches = state_manager.get_all_completed_tasks('big_summary', sub_stage_name)
    fallback_files = [
        filepath for filepath in all_files
        if _path_starts_with_any_batch_name(filepath, completed_batches)
    ]
    if fallback_files:
        sub_stage_label = "剧情" if sub_stage_name == "plot" else "角色"
        log_message(
            log_callback,
            f"未找到当前 API 名称后缀的大总结文件，已使用导入项目中的旧后缀大总结继续生成{sub_stage_label}超级总结。",
            api_id=api_display_name,
            status="WARN",
        )
        fallback_files.sort(key=get_big_summary_sort_key)
    return fallback_files

def _completed_with_output(
    state_manager: sm.StateManager,
    task_name: str,
    stage_name: str,
    output_path: str,
) -> bool:
    return state_manager.is_task_complete(task_name, stage_name) and os.path.isfile(output_path)

async def run_small_summary_stage(
    pending_tasks: List[str], api_configs: List[Dict], prompts: Dict[str, Dict],
    novel_folder_path: str, log_callback: Callable, pause_event: asyncio.Event,
    state_manager: sm.StateManager, word_counts: Dict[str, str]
):
    api_work_distribution = _distribute_chapters_sequentially(pending_tasks, api_configs)

    for api_id, units in api_work_distribution.items():
        if not units: continue
        api_config = next((ac for ac in api_configs if ac['id'] == api_id), None)
        if api_config:
            api_display_name = api_config.get('api_key_name', api_id)
            chapter_names = [os.path.basename(u) for u in units]
            log_message(log_callback, f"分配了 {len(units)} 个小结任务: {', '.join(chapter_names)}", api_id=api_display_name, status="INFO")

    tasks = [
        process_small_summary_units_for_api(
            novel_folder_path, next((ac for ac in api_configs if ac['id'] == api_id), None),
            units, prompts, word_counts, log_callback, pause_event, state_manager
        ) for api_id, units in api_work_distribution.items() if units
    ]
    await asyncio.gather(*tasks)

async def process_small_summary_units_for_api(
    novel_folder_path: str, api_config: Dict, units_for_this_api: List[str],
    prompts: Dict, word_counts: Dict, log_callback: Callable,
    pause_event: asyncio.Event, state_manager: sm.StateManager
):
    api_display_name = api_config.get('api_key_name', 'UnknownAPI')
    api_id = api_config['id']

    for i, chapter_path in enumerate(units_for_this_api):
        task_name = os.path.basename(chapter_path)
        try:
            await check_pause_async(pause_event)
            summary_text = await process_single_chapter_async(
                chapter_path, api_config, prompts, word_counts,
                log_callback, pause_event, i, len(units_for_this_api)
            )
            if summary_text is None: raise Exception(f"LLM call for {task_name} failed.")

            char_block = extract_character_info_from_summary(summary_text)
            plot_block = extract_summary_content(summary_text)
            if not plot_block:
                plot_block = summary_text.replace(char_block, "").strip()

            plot_output_path = os.path.join(get_summarizer_cache_dir(novel_folder_path), USER_FACING_SMALL_PLOT_SUBDIR, task_name)
            char_output_path = os.path.join(get_summarizer_cache_dir(novel_folder_path), USER_FACING_SMALL_CHAR_SUBDIR, task_name)
            
            os.makedirs(os.path.dirname(plot_output_path), exist_ok=True)
            os.makedirs(os.path.dirname(char_output_path), exist_ok=True)
            
            async with aiofiles.open(plot_output_path, 'w', encoding='utf-8') as f: await f.write(plot_block)
            async with aiofiles.open(char_output_path, 'w', encoding='utf-8') as f: await f.write(char_block)
            
            state_manager.mark_task_complete(task_name, 'small_summary', api_id=api_id)
        except asyncio.CancelledError:
            log_message(log_callback, f"任务在处理章节 {task_name} 时被取消。", api_id=api_display_name, status="WARN")
            raise
        except Exception as e:
            log_message(log_callback, f"处理章节 {task_name} 时发生错误: {e}", api_id=api_display_name, status="FAIL", traceback_info=traceback.format_exc())
            raise e
    log_message(log_callback, f"已完成其分配的 {len(units_for_this_api)} 个小结任务。", api_id=api_display_name, status="SUCCESS")

async def process_single_chapter_async(
    chapter_path: str, api_config: Dict, prompts: Dict,
    word_counts: Dict, log_callback: Callable, pause_event: asyncio.Event,
    chapter_index: int, total_chapters: int
):
    api_display_name = api_config.get('api_key_name', 'UnknownAPI')
    task_name = os.path.basename(chapter_path)
    log_message(log_callback, f"开始处理章节 '{task_name}' ({chapter_index + 1}/{total_chapters})", api_id=api_display_name, status="START")
    
    content = await utils.read_file_content_robustly_async(chapter_path)
    
    summary_text = await get_llm_summary_with_config(
        api_config, prompts['prompt_small_summary'], 
        {
            'filename_for_context': task_name,
            'first_chunk_guidance': "这是章节的全部内容。",
            'current_chunk_text': content
        },
        log_callback,
        task_info={
            'novel_folder_path': os.path.dirname(chapter_path),
            'stage': 'small_summary',
            'source_file': chapter_path,
            'source_char_count': len(content),
            'progress_text': f"小总结 {task_name}",
        },
        plot_word_count=word_counts.get("small_plot_word_count"),
        char_word_count=word_counts.get("small_char_word_count")
    )
    return summary_text

async def run_big_summary_stage(
    pending_batches: List[Tuple[str, List[str]]], sub_stage_name: str, api_configs: List[Dict], prompts: Dict,
    novel_folder_path: str, log_callback: Callable, pause_event: asyncio.Event,
    state_manager: sm.StateManager, word_counts: Dict
):
    api_work_distribution = _distribute_batches_sequentially(pending_batches, api_configs)

    for api_id, batches in api_work_distribution.items():
        if not batches: continue
        api_config = next((ac for ac in api_configs if ac['id'] == api_id), None)
        if api_config:
            api_display_name = api_config.get('api_key_name', api_id)
            batch_names = [b[0] for b in batches]
            log_message(log_callback, f"分配了 {len(batches)} 个 '{sub_stage_name}' 大总结批次: {', '.join(batch_names)}", api_id=api_display_name, status="INFO")

    tasks = [
        process_big_summary_units_for_api(
            novel_folder_path, next((ac for ac in api_configs if ac['id'] == api_id), None),
            units, sub_stage_name, prompts, word_counts, log_callback, pause_event, state_manager
        ) for api_id, units in api_work_distribution.items() if units
    ]
    await asyncio.gather(*tasks)

async def process_big_summary_units_for_api(
    novel_folder_path: str, api_config: Dict, batches_for_this_api: List[Tuple[str, List[str]]],
    sub_stage_name: str, prompts: Dict, word_counts: Dict,
    log_callback: Callable, pause_event: asyncio.Event, state_manager: sm.StateManager
):
    api_display_name = api_config.get('api_key_name', 'UnknownAPI')
    for i, (batch_name, batch_content_paths) in enumerate(batches_for_this_api):
        try:
            await check_pause_async(pause_event)
            await process_summary_batch_async(
                api_config, batch_content_paths, f"big_{sub_stage_name}",
                prompts, word_counts, log_callback, pause_event, batch_name,
                i, len(batches_for_this_api), novel_folder_path, state_manager
            )
        except asyncio.CancelledError:
            log_message(log_callback, f"任务在处理大总结批次 {batch_name} ({sub_stage_name}) 时被取消。", api_id=api_display_name, status="WARN")
            raise
        except Exception as e:
            log_message(log_callback, f"处理大总结批次 {batch_name} ({sub_stage_name}) 时失败: {e}", api_id=api_display_name, status="FAIL", traceback_info=traceback.format_exc())
            raise e

async def run_super_summary_for_api(
    api_config: Dict,
    novel_folder_path: str,
    prompts: Dict,
    word_counts: Dict,
    log_callback: Callable,
    pause_event: asyncio.Event,
    state_manager: sm.StateManager,
    big_summary_batch_size: int = 5
):
    """
    为单个API执行完整的超级总结P1和P2流程。
    输入是该API之前生成的所有大总结文件。
    """
    api_id = api_config['id']
    api_display_name = api_config.get('api_key_name', api_id)
    sane_api_name = sanitize_api_name(api_display_name)
    cache_dir = get_summarizer_cache_dir(novel_folder_path)

    # --- 处理剧情 ---
    task_plot_p1_name = f"super_summary_{api_id}_plot_p1"
    task_plot_p2_name = f"super_summary_{api_id}_plot_p2"

    # 1. 找到该API之前生成的所有剧情大总结文件
    plot_files_for_api = _select_big_summary_files_for_api(
        cache_dir,
        USER_FACING_BIG_PLOT_SUBDIR,
        sane_api_name,
        state_manager,
        api_id,
        'plot',
        big_summary_batch_size,
        log_callback,
        api_display_name,
    )
    
    if plot_files_for_api:
        log_message(log_callback, f"为 {api_display_name} 检查超级剧情总结...", api_id=api_display_name, status="INFO")
        plot_context = await utils.read_files_and_join(plot_files_for_api)
        p1_plot_path = os.path.join(cache_dir, USER_FACING_SUPER_PLOT_P1_SUBDIR, f"super_summary_{sane_api_name}_plot_p1.txt")
        p2_plot_path = os.path.join(cache_dir, USER_FACING_SUPER_PLOT_P2_SUBDIR, f"super_summary_{sane_api_name}_plot_p2.txt")
        
        # 2. 生成P1
        if not _completed_with_output(state_manager, task_plot_p1_name, 'super_summary', p1_plot_path):
            log_message(log_callback, f"开始生成超级剧情总结 P1", api_id=api_display_name, status="START")
            p1_plot_summary = await get_llm_summary_with_config(
                api_config, prompts['prompt_super_plot_p1'], 
                {'combined_all_big_plot_summaries_text': plot_context},
                log_callback,
                task_info={
                    'novel_folder_path': novel_folder_path,
                    'stage': 'super_summary_plot_p1',
                    'source_files': plot_files_for_api,
                    'source_char_count': len(plot_context),
                    'progress_text': '超级剧情总结 P1',
                },
                super_plot_p1_word_count=word_counts.get("super_plot_p1_word_count")
            )
            if p1_plot_summary:
                os.makedirs(os.path.dirname(p1_plot_path), exist_ok=True)
                async with aiofiles.open(p1_plot_path, 'w', encoding='utf-8') as f: await f.write(p1_plot_summary)
                state_manager.mark_task_complete(task_plot_p1_name, 'super_summary')
                log_message(log_callback, f"已生成超级剧情总结 P1", api_id=api_display_name, status="SUCCESS")
        else:
            log_message(log_callback, "超级剧情总结 P1 已完成，跳过。", api_id=api_display_name, status="INFO")

        # 3. 生成P2 (使用相同的上下文)
        if not _completed_with_output(state_manager, task_plot_p2_name, 'super_summary', p2_plot_path):
            log_message(log_callback, f"开始生成超级剧情总结 P2", api_id=api_display_name, status="START")
            p2_plot_summary = await get_llm_summary_with_config(
                api_config, prompts['prompt_super_plot_p2'], 
                {'combined_all_big_plot_summaries_text': plot_context},
                log_callback,
                task_info={
                    'novel_folder_path': novel_folder_path,
                    'stage': 'super_summary_plot_p2',
                    'source_files': plot_files_for_api,
                    'source_char_count': len(plot_context),
                    'progress_text': '超级剧情总结 P2',
                },
                super_plot_p2_word_count=word_counts.get("super_plot_p2_word_count")
            )
            if p2_plot_summary:
                os.makedirs(os.path.dirname(p2_plot_path), exist_ok=True)
                async with aiofiles.open(p2_plot_path, 'w', encoding='utf-8') as f: await f.write(p2_plot_summary)
                state_manager.mark_task_complete(task_plot_p2_name, 'super_summary')
                log_message(log_callback, f"已生成超级剧情总结 P2", api_id=api_display_name, status="SUCCESS")
        else:
            log_message(log_callback, "超级剧情总结 P2 已完成，跳过。", api_id=api_display_name, status="INFO")

    # --- 处理角色 (逻辑同上) ---
    task_char_p1_name = f"super_summary_{api_id}_char_p1"
    task_char_p2_name = f"super_summary_{api_id}_char_p2"

    char_files_for_api = _select_big_summary_files_for_api(
        cache_dir,
        USER_FACING_BIG_CHAR_SUBDIR,
        sane_api_name,
        state_manager,
        api_id,
        'char',
        big_summary_batch_size,
        log_callback,
        api_display_name,
    )
    
    if char_files_for_api:
        log_message(log_callback, f"为 {api_display_name} 检查超级角色总结...", api_id=api_display_name, status="INFO")
        char_context = await utils.read_files_and_join(char_files_for_api)
        p1_char_path = os.path.join(cache_dir, USER_FACING_SUPER_CHAR_P1_SUBDIR, f"super_summary_{sane_api_name}_char_p1.txt")
        p2_char_path = os.path.join(cache_dir, USER_FACING_SUPER_CHAR_P2_SUBDIR, f"super_summary_{sane_api_name}_char_p2.txt")

        # 生成P1
        if not _completed_with_output(state_manager, task_char_p1_name, 'super_summary', p1_char_path):
            log_message(log_callback, f"开始生成超级角色总结 P1", api_id=api_display_name, status="START")
            p1_char_summary = await get_llm_summary_with_config(
                api_config, prompts['prompt_super_char_p1'],
                {'combined_all_big_character_summaries_text': char_context},
                log_callback,
                task_info={
                    'novel_folder_path': novel_folder_path,
                    'stage': 'super_summary_char_p1',
                    'source_files': char_files_for_api,
                    'source_char_count': len(char_context),
                    'progress_text': '超级角色总结 P1',
                },
                super_char_p1_word_count=word_counts.get("super_char_p1_word_count")
            )
            if p1_char_summary:
                os.makedirs(os.path.dirname(p1_char_path), exist_ok=True)
                async with aiofiles.open(p1_char_path, 'w', encoding='utf-8') as f: await f.write(p1_char_summary)
                state_manager.mark_task_complete(task_char_p1_name, 'super_summary')
                log_message(log_callback, f"已生成超级角色总结 P1", api_id=api_display_name, status="SUCCESS")
        else:
            log_message(log_callback, "超级角色总结 P1 已完成，跳过。", api_id=api_display_name, status="INFO")

        # 生成P2
        if not _completed_with_output(state_manager, task_char_p2_name, 'super_summary', p2_char_path):
            log_message(log_callback, f"开始生成超级角色总结 P2", api_id=api_display_name, status="START")
            p2_char_summary = await get_llm_summary_with_config(
                api_config, prompts['prompt_super_char_p2'],
                {'combined_all_big_character_summaries_text': char_context},
                log_callback,
                task_info={
                    'novel_folder_path': novel_folder_path,
                    'stage': 'super_summary_char_p2',
                    'source_files': char_files_for_api,
                    'source_char_count': len(char_context),
                    'progress_text': '超级角色总结 P2',
                },
                super_char_p2_word_count=word_counts.get("super_char_p2_word_count")
            )
            if p2_char_summary:
                os.makedirs(os.path.dirname(p2_char_path), exist_ok=True)
                async with aiofiles.open(p2_char_path, 'w', encoding='utf-8') as f: await f.write(p2_char_summary)
                state_manager.mark_task_complete(task_char_p2_name, 'super_summary')
                log_message(log_callback, f"已生成超级角色总结 P2", api_id=api_display_name, status="SUCCESS")
        else:
            log_message(log_callback, "超级角色总结 P2 已完成，跳过。", api_id=api_display_name, status="INFO")

async def run_ultimate_summary_stage(
    api_config: Dict,
    novel_folder_path: str,
    prompts: Dict,
    word_counts: Dict,
    log_callback: Callable,
    pause_event: asyncio.Event,
    state_manager: sm.StateManager
):
    """
    执行终极总结流程。
    输入是所有API之前生成的所有超级总结P1和P2文件。
    """
    api_id = api_config['id']
    api_display_name = api_config.get('api_key_name', api_id)
    sane_api_name = sanitize_api_name(api_display_name)
    cache_dir = get_summarizer_cache_dir(novel_folder_path)
    log_message(log_callback, f"终极总结API ({api_display_name}) 开始整合所有超级总结...", api_id=api_display_name, status="START")

    # 定义要处理的四个部分
    ultimate_parts = [
        ('plot', 'p1', USER_FACING_SUPER_PLOT_P1_SUBDIR, 'prompt_ultimate_plot_p1', 'combined_all_plot_p1_summaries', USER_FACING_ULTIMATE_PLOT_P1_SUBDIR, 'ultimate_plot_p1_word_count'),
        ('plot', 'p2', USER_FACING_SUPER_PLOT_P2_SUBDIR, 'prompt_ultimate_plot_p2', 'combined_all_plot_p2_summaries', USER_FACING_ULTIMATE_PLOT_P2_SUBDIR, 'ultimate_plot_p2_word_count'),
        ('char', 'p1', USER_FACING_SUPER_CHAR_P1_SUBDIR, 'prompt_ultimate_char_p1', 'combined_all_char_p1_summaries', USER_FACING_ULTIMATE_CHAR_P1_SUBDIR, 'ultimate_char_p1_word_count'),
        ('char', 'p2', USER_FACING_SUPER_CHAR_P2_SUBDIR, 'prompt_ultimate_char_p2', 'combined_all_char_p2_summaries', USER_FACING_ULTIMATE_CHAR_P2_SUBDIR, 'ultimate_char_p2_word_count')
    ]

    for part_info in ultimate_parts:
        category, part_num, source_subdir, prompt_key, context_key, output_subdir, wc_key = part_info
        
        task_name = f"ultimate_summary_{category}_{part_num}"

        await check_pause_async(pause_event)

        if state_manager.is_task_complete(task_name, 'ultimate_summary'):
            log_message(log_callback, f"终极总结: {category} - {part_num} 已完成，跳过。", api_id=api_display_name, status="INFO")
            continue

        log_message(log_callback, f"开始生成终极总结: {category} - {part_num}", api_id=api_display_name, status="INFO")

        source_dir = os.path.join(cache_dir, source_subdir)
        if not os.path.isdir(source_dir):
            log_message(log_callback, f"未找到源目录 {source_dir}，跳过 {category}-{part_num}", api_id=api_display_name, status="WARN")
            continue
            
        source_files = [os.path.join(source_dir, f) for f in os.listdir(source_dir) if f.endswith(".txt")]
        source_files.sort(key=get_super_ultimate_summary_sort_key)
        if not source_files:
            log_message(log_callback, f"目录 {source_dir} 为空，跳过 {category}-{part_num}", api_id=api_display_name, status="WARN")
            continue

        context = await utils.read_files_and_join(source_files)
        
        summary = await get_llm_summary_with_config(
            api_config, prompts[prompt_key],
            {context_key: context},
            log_callback,
            task_info={
                'novel_folder_path': novel_folder_path,
                'stage': task_name,
                'source_files': source_files,
                'source_char_count': len(context),
                'progress_text': f"终极总结 {category}-{part_num}",
            },
            **{wc_key: word_counts.get(wc_key)}
        )

        if summary:
            output_path = os.path.join(cache_dir, output_subdir, f"ultimate_summary_{category}_{part_num}_by_{sane_api_name}.txt")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            async with aiofiles.open(output_path, 'w', encoding='utf-8') as f: await f.write(summary)
            state_manager.mark_task_complete(task_name, 'ultimate_summary')
            log_message(log_callback, f"成功生成终极总结: {category} - {part_num}", api_id=api_display_name, status="SUCCESS")

    # 在所有部分都检查/完成后，我们不再需要一个总的完成标记，因为协调器会检查所有子任务。
    # state_manager.mark_task_complete('ultimate_summary', 'ultimate_summary')

async def process_summary_batch_async(
    api_config: Dict, batch_files: List[str], task_type: str,
    prompts: Dict, word_counts: Dict, log_callback: Callable,
    pause_event: asyncio.Event, batch_name: str, batch_index: int,
    total_batches: int, novel_folder_path: str, state_manager: sm.StateManager
):
    api_display_name = api_config.get('api_key_name', 'UnknownAPI')
    sane_api_name = sanitize_api_name(api_display_name)
    stage, sub_stage = task_type.split('_')
    log_message(log_callback, f"开始处理批次 '{batch_name}' ({batch_index + 1}/{total_batches})", api_id=api_display_name, status="START")

    # 根据任务类型(大总结/超级总结)和子阶段(剧情/角色)选择正确的提示词
    # 注意：根据新流程，超级总结有自己的独立函数，这里不再处理
    if stage == 'big':
        prompt_config = prompts.get(f'prompt_big_{sub_stage}')
        if sub_stage == 'plot':
            context_key = 'concatenated_small_plot_summaries'
            word_count_key = 'big_plot_word_count'
        else: # char
            context_key = 'concatenated_small_character_summaries'
            word_count_key = 'big_char_word_count'
    else:
        log_message(log_callback, f"未知的任务类型 '{stage}' in process_summary_batch_async", "global", "ERROR")
        return

    # 批处理描述后缀
    batch_description_suffix = f" (批次: {batch_name})"

    # 异步读取所有文件内容并合并
    content = await utils.read_files_and_join(batch_files)
    
    # 构建传递给LLM的参数字典
    llm_params = {
        context_key: content,
        'batch_description_suffix': batch_description_suffix
    }
    # 动态添加字数统计，因为**kwargs不支持重复键
    if stage == 'big':
        llm_params[word_count_key] = word_counts.get(word_count_key)

    # 调用LLM API
    summary_text = await get_llm_summary_with_config(
        api_config, prompt_config, 
        llm_params,
        log_callback,
        task_info={
            'novel_folder_path': novel_folder_path,
            'stage': task_type,
            'batch_name': batch_name,
            'source_files': batch_files,
            'source_char_count': len(content),
            'progress_text': f"{task_type} {batch_name}",
        },
    )

    if summary_text is None:
        raise Exception(f"LLM call for batch {batch_name} failed.")

    # 定义输出目录
    output_dir_map = {
        'big_plot': USER_FACING_BIG_PLOT_SUBDIR,
        'big_char': USER_FACING_BIG_CHAR_SUBDIR,
    }
    output_dir = os.path.join(get_summarizer_cache_dir(novel_folder_path), output_dir_map[task_type])
    os.makedirs(output_dir, exist_ok=True)

    # 终极输出文件名修改，加入api_id标识
    output_filename = f"{batch_name}_{sane_api_name}.txt"
    output_filepath = os.path.join(output_dir, output_filename)

    # 保存文件
    async with aiofiles.open(output_filepath, 'w', encoding='utf-8') as f:
        await f.write(summary_text)

    # 标记任务完成
    state_manager.mark_task_complete(batch_name, 'big_summary', sub_stage)
    log_message(log_callback, f"批次 '{batch_name}' 处理完成", api_id=api_display_name, status="SUCCESS")
