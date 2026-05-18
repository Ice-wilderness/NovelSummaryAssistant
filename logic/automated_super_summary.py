"""
This module contains the logic for the new automated super-summary stage.
It groups all big summaries, batches them, and distributes them evenly among APIs.
"""

import os
import asyncio
import traceback
import aiofiles
import math
from typing import Dict, List, Callable, Tuple
from python.logic.utils import read_files_and_join, get_big_summary_sort_key
from . import state_manager as sm
from python.logic.llm_api import get_llm_summary_with_config
from python.logic.utils import (
    log_message, check_pause_async, get_summarizer_cache_dir,
    sanitize_api_name, read_files_and_join
)
from python.logic.prompts import (
    USER_FACING_SUPER_PLOT_P1_SUBDIR, USER_FACING_SUPER_PLOT_P2_SUBDIR,
    USER_FACING_SUPER_CHAR_P1_SUBDIR, USER_FACING_SUPER_CHAR_P2_SUBDIR,
    USER_FACING_BIG_PLOT_SUBDIR, USER_FACING_BIG_CHAR_SUBDIR
)

def _get_all_big_summary_files(cache_dir: str, sub_stage_name: str) -> List[str]:
    """获取指定子阶段（plot或char）的所有大总结文件。"""
    if sub_stage_name not in ['plot', 'char']:
        return []
    
    target_dir = os.path.join(cache_dir, USER_FACING_BIG_PLOT_SUBDIR if sub_stage_name == 'plot' else USER_FACING_BIG_CHAR_SUBDIR)
    
    if not os.path.isdir(target_dir):
        return []
        
    all_files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith('.txt')]
    all_files.sort(key=get_big_summary_sort_key)
    return all_files

def _create_batches(files: List[str], batch_size: int) -> List[List[str]]:
    """根据给定的批量大小，将文件列表分割成多个批次。"""
    if not files or batch_size <= 0:
        return []
    return [files[i:i + batch_size] for i in range(0, len(files), batch_size)]

def _distribute_batches_evenly(batches: List[List[str]], api_configs: List[Dict]) -> Dict[str, List[Tuple[str, List[str]]]]:
    """将批次尽可能均匀地分配给可用的API。"""
    distribution = {api['id']: [] for api in api_configs}
    api_ids = [api['id'] for api in api_configs]
    
    for i, batch in enumerate(batches):
        api_id_for_this_batch = api_ids[i % len(api_ids)]
        # 为每个批次创建一个唯一的名称
        batch_name = f"auto_batch_{i+1}"
        distribution[api_id_for_this_batch].append((batch_name, batch))
        
    return distribution

async def _process_super_summary_batch_for_api(
    api_config: Dict,
    batch_name: str,
    file_paths: List[str],
    sub_stage_name: str,
    novel_folder_path: str,
    prompts: Dict,
    word_counts: Dict,
    log_callback: Callable,
    pause_event: asyncio.Event,
    state_manager: sm.StateManager,
    batch_index: int,
    total_batches: int
):
    """处理单个API的单个超级总结批次（包括P1和P2）。"""
    api_id = api_config['id']
    api_display_name = api_config.get('api_key_name', api_id)
    cache_dir = get_summarizer_cache_dir(novel_folder_path)

    log_message(log_callback, f"开始处理超级{sub_stage_name}总结批次 '{batch_name}' ({batch_index + 1}/{total_batches})", api_id=api_display_name, status="START")

    try:
        await check_pause_async(pause_event)
        
        context = await read_files_and_join(file_paths)
        if not context:
            log_message(log_callback, f"批次 '{batch_name}' 的内容为空，跳过。", api_id=api_display_name, status="WARN")
            return

        # --- 生成 P1 ---
        prompt_key_p1 = f"prompt_super_{sub_stage_name}_p1"
        wc_key_p1 = f"super_{sub_stage_name}_p1_word_count"
        output_dir_p1 = os.path.join(cache_dir, USER_FACING_SUPER_PLOT_P1_SUBDIR if sub_stage_name == 'plot' else USER_FACING_SUPER_CHAR_P1_SUBDIR)
        
        p1_summary = await get_llm_summary_with_config(
            api_config, prompts.get(prompt_key_p1),
            {'combined_all_big_summaries_text': context}, # 使用与旧版一致的变量名
            log_callback, **{wc_key_p1: word_counts.get(wc_key_p1)}
        )
        if p1_summary:
            p1_output_path = os.path.join(output_dir_p1, f"super_summary_{batch_name}_{sub_stage_name}_p1.txt")
            os.makedirs(os.path.dirname(p1_output_path), exist_ok=True)
            async with aiofiles.open(p1_output_path, 'w', encoding='utf-8') as f: await f.write(p1_summary)
            log_message(log_callback, f"已生成批次 '{batch_name}' 的超级{sub_stage_name}总结 P1", api_id=api_display_name, status="SUCCESS")

        # --- 生成 P2 ---
        prompt_key_p2 = f"prompt_super_{sub_stage_name}_p2"
        wc_key_p2 = f"super_{sub_stage_name}_p2_word_count"
        output_dir_p2 = os.path.join(cache_dir, USER_FACING_SUPER_PLOT_P2_SUBDIR if sub_stage_name == 'plot' else USER_FACING_SUPER_CHAR_P2_SUBDIR)

        p2_summary = await get_llm_summary_with_config(
            api_config, prompts.get(prompt_key_p2),
            {'combined_all_big_summaries_text': context},
            log_callback, **{wc_key_p2: word_counts.get(wc_key_p2)}
        )
        if p2_summary:
            p2_output_path = os.path.join(output_dir_p2, f"super_summary_{batch_name}_{sub_stage_name}_p2.txt")
            os.makedirs(os.path.dirname(p2_output_path), exist_ok=True)
            async with aiofiles.open(p2_output_path, 'w', encoding='utf-8') as f: await f.write(p2_summary)
            log_message(log_callback, f"已生成批次 '{batch_name}' 的超级{sub_stage_name}总结 P2", api_id=api_display_name, status="SUCCESS")

        # 标记这个自动批次为完成
        state_manager.mark_task_complete(batch_name, f'super_summary_{sub_stage_name}', api_id)

    except asyncio.CancelledError:
        log_message(log_callback, f"处理批次 '{batch_name}' 时任务被取消。", api_id=api_display_name, status="WARN")
        raise
    except Exception as e:
        log_message(log_callback, f"处理批次 '{batch_name}' 时发生错误: {e}", api_id=api_display_name, status="FAIL", traceback_info=traceback.format_exc())
        raise

async def run_automated_super_summary_stage(
    active_api_configs: List[Dict],
    novel_folder_path: str,
    prompts: Dict,
    word_counts: Dict,
    log_callback: Callable,
    pause_event: asyncio.Event,
    state_manager: sm.StateManager,
    super_summary_threshold: int
):
    """
    执行自动化的超级总结阶段。
    """
    cache_dir = get_summarizer_cache_dir(novel_folder_path)
    
    for sub_stage in ['plot', 'char']:
        log_message(log_callback, f"--- 开始自动超级[{sub_stage}]总结阶段 ---", status="INFO", api_id="global")
        
        all_files = _get_all_big_summary_files(cache_dir, sub_stage)
        
        if not all_files:
            log_message(log_callback, f"未找到任何“大{sub_stage}总结”文件，跳过该阶段。", status="INFO", api_id="global")
            continue

        all_batches = _create_batches(all_files, super_summary_threshold)
        
        # 筛选出未完成的批次
        pending_batches = []
        for i, batch_files in enumerate(all_batches):
            batch_name = f"auto_batch_{i+1}"
            if not state_manager.is_task_complete(batch_name, f'super_summary_{sub_stage}'):
                pending_batches.append(batch_files)
        
        if not pending_batches:
            log_message(log_callback, f"所有“超级{sub_stage}总结”批次均已完成。", status="INFO", api_id="global")
            continue

        log_message(log_callback, f"共找到 {len(all_files)} 个大{sub_stage}总结文件，创建了 {len(pending_batches)}/{len(all_batches)} 个待处理批次。", status="INFO", api_id="global")

        # 将未完成的批次重新命名并分发
        renamed_pending_batches = [(f"auto_batch_{i+1}", files) for i, files in enumerate(pending_batches)]
        
        # 使用均匀分配
        distribution = {api['id']: [] for api in active_api_configs}
        api_ids = [api['id'] for api in active_api_configs]
        for i, (name, files) in enumerate(renamed_pending_batches):
             api_id_for_this_batch = api_ids[i % len(api_ids)]
             distribution[api_id_for_this_batch].append((name, files))

        # 创建任务
        all_tasks = []
        for api_id, assigned_batches in distribution.items():
            if not assigned_batches:
                continue
            
            api_config = next((ac for ac in active_api_configs if ac['id'] == api_id), None)
            api_display_name = api_config.get('api_key_name', api_id)
            batch_names = [b[0] for b in assigned_batches]
            log_message(log_callback, f"API '{api_display_name}' 分配到 {len(assigned_batches)} 个超级{sub_stage}总结批次: {', '.join(batch_names)}", api_id=api_display_name, status="INFO")

            for i, (batch_name, file_paths) in enumerate(assigned_batches):
                task = asyncio.create_task(_process_super_summary_batch_for_api(
                    api_config, batch_name, file_paths, sub_stage, novel_folder_path,
                    prompts, word_counts, log_callback, pause_event, state_manager,
                    i, len(assigned_batches)
                ))
                all_tasks.append(task)
        
        if all_tasks:
            await asyncio.gather(*all_tasks)
        
        log_message(log_callback, f"--- 自动超级[{sub_stage}]总结阶段完成 ---", status="SUCCESS", api_id="global")

    return True 
