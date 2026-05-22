"""
This module contains the core, stateful processing logic for the novel summarization task.
It acts as an orchestrator, calling other modules to perform specific tasks.
"""

import os
import asyncio
import traceback

from logic.state_manager import StateManager
from logic.utils import log_message, load_all_prompts_for_run, check_pause_async

from logic.summarization_stages import (
    run_small_summary_stage,
    run_big_summary_stage,
    run_super_summary_for_api,
    run_ultimate_summary_stage
)
from logic.automated_super_summary import run_automated_super_summary_stage

async def run_summarization_process(
    novel_folder_path,
    active_api_configs,
    log_callback,
    pause_event,
    summary_batch_size,
    big_summary_batch_size,
    super_summary_threshold,
    ultimate_api_id,
    word_counts,
    use_fine_grained_flow,
    stop_after_small_summary=False
):
    """
    Orchestrates the entire summarization process using a state-driven loop.
    This is the main entry point that sets up and runs the async orchestrator.
    """
    try:
        return await async_orchestrator(
            novel_folder_path, active_api_configs, log_callback, pause_event,
            summary_batch_size, big_summary_batch_size, super_summary_threshold, ultimate_api_id, word_counts,
            use_fine_grained_flow, stop_after_small_summary
        )
    except Exception as e:
        tb_info = traceback.format_exc()
        log_message(log_callback, f"任务启动时发生严重错误: {e}", "FAIL", traceback_info=tb_info)
        return False

async def _run_small_summary_for_api(
    api_config,
    chapters_for_api,
    novel_folder_path,
    prompts,
    log_callback,
    pause_event,
    state_manager,
    word_counts,
    summary_batch_size,
):
    api_id = api_config['id']
    api_display_name = api_config.get('api_key_name', api_id)
    pending_small_for_api = state_manager.get_pending_small_summary_chapters(
        chapters_for_api,
        batch_size=summary_batch_size,
    )
    if not pending_small_for_api:
        log_message(log_callback, f"--- {api_display_name}: 小总结阶段已完成，跳过。 ---", status="INFO", api_id=api_display_name)
        return

    log_message(log_callback, f"--- {api_display_name}: 开始小总结阶段，有 {len(pending_small_for_api)} 个待处理章节 ---", status="INFO", api_id=api_display_name)
    await run_small_summary_stage(
        pending_small_for_api, [api_config], prompts, novel_folder_path,
        log_callback, pause_event, state_manager, word_counts, summary_batch_size
    )


async def _run_small_and_big_summary_for_api(
    api_config,
    chapters_for_api,
    novel_folder_path,
    prompts,
    log_callback,
    pause_event,
    state_manager,
    word_counts,
    summary_batch_size,
    big_summary_batch_size
):
    """
    为单个API执行小总结和大总结阶段。
    """
    api_id = api_config['id']
    api_display_name = api_config.get('api_key_name', api_id)
    log_message(log_callback, f"API '{api_display_name}' 开始执行小结/大结任务...", status="INFO", api_id=api_display_name)

    # 1. 小总结
    await _run_small_summary_for_api(
        api_config, chapters_for_api, novel_folder_path, prompts,
        log_callback, pause_event, state_manager, word_counts, summary_batch_size
    )

    # 2. 大总结 (剧情和角色)
    for sub_stage in ['plot', 'char']:
        pending_big_batches = state_manager.get_pending_tasks('big_summary', sub_stage_name=sub_stage, batch_size=big_summary_batch_size, api_id=api_id)
        if pending_big_batches:
            log_message(log_callback, f"--- {api_display_name}: 开始 {sub_stage} 大总结阶段，有 {len(pending_big_batches)} 个批次 ---", status="INFO", api_id=api_display_name)
            await run_big_summary_stage(
                pending_big_batches, sub_stage, [api_config], prompts, novel_folder_path,
                log_callback, pause_event, state_manager, word_counts
            )
    
    log_message(log_callback, f"API '{api_display_name}' 的小结/大结任务已完成。", status="SUCCESS", api_id=api_display_name)


async def _run_full_pipeline_for_api(
    api_config,
    chapters_for_api,
    novel_folder_path,
    prompts,
    log_callback,
    pause_event,
    state_manager,
    word_counts,
    summary_batch_size,
    big_summary_batch_size
):
    """
    为单个API执行从头到尾的完整流程，包括小结、大结和超级总结。
    """
    api_id = api_config['id']
    api_display_name = api_config.get('api_key_name', api_id)
    log_message(log_callback, f"API '{api_display_name}' 开始执行独立完整流程...", status="INFO", api_id=api_display_name)

    # --- 第一部分：执行小结/大结 ---
    await _run_small_and_big_summary_for_api(
        api_config, chapters_for_api, novel_folder_path, prompts,
        log_callback, pause_event, state_manager, word_counts, summary_batch_size, big_summary_batch_size
    )
    
    log_message(log_callback, f"API '{api_display_name}' 的小结/大结任务已完成，立即开始超级总结...", status="INFO", api_id=api_display_name)
    
    await check_pause_async(pause_event)

    # --- 第二部分：立刻开始超级总结 ---
    await run_super_summary_for_api(
        api_config, novel_folder_path, prompts, word_counts,
        log_callback, pause_event, state_manager, big_summary_batch_size
    )
    
    log_message(log_callback, f"API '{api_display_name}' 的独立完整流程（包括超级总结）已全部完成。", status="SUCCESS", api_id=api_display_name)


async def async_orchestrator(
    novel_folder_path, active_api_configs, log_callback, pause_event,
    summary_batch_size, big_summary_batch_size, super_summary_threshold, ultimate_api_id, word_counts,
    use_fine_grained_flow, stop_after_small_summary=False
):
    """
    The asynchronous core of the summarization process.
    """
    try:
        if not active_api_configs:
            log_message(log_callback, "错误：没有活动的API配置。请至少启用一个API。", status="FAIL", api_id="global")
            return False

        prompts = load_all_prompts_for_run()
        state_manager = StateManager(novel_folder_path)
        
        init_log = state_manager.get_initialization_log()
        if init_log:
            log_message(log_callback, init_log, status="SYSTEM_INFO", api_id="global")

        if not state_manager.chapters:
            log_message(log_callback, "错误：在源文件夹中未找到任何有效的 .txt 章节文件。", status="FAIL", api_id="global")
            return False

        await check_pause_async(pause_event)

        from logic.utils import _distribute_chapters_sequentially
        chapter_distribution = _distribute_chapters_sequentially(state_manager.chapters, active_api_configs)

        if stop_after_small_summary:
            log_message(log_callback, "--- 开始执行[仅小总结]模式：完成小总结后停止 ---", status="INFO", api_id="global")
            small_summary_tasks = []
            for api_config in active_api_configs:
                api_id = api_config['id']
                chapters_for_this_api = chapter_distribution.get(api_id, [])
                if chapters_for_this_api:
                    task = asyncio.create_task(_run_small_summary_for_api(
                        api_config, chapters_for_this_api, novel_folder_path, prompts,
                        log_callback, pause_event, state_manager, word_counts, summary_batch_size
                    ))
                    small_summary_tasks.append(task)

            if small_summary_tasks:
                results = await asyncio.gather(*small_summary_tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, asyncio.CancelledError):
                        log_message(log_callback, "一个小总结处理任务被取消。", status="INFO", api_id="global")
                        raise asyncio.CancelledError
                    elif isinstance(res, Exception):
                        raise res

            log_message(log_callback, "--- 仅小总结模式已完成，后续大总结、超级总结和终极总结已跳过。 ---", status="SUCCESS", api_id="global")
            return True

        # --- 【核心修改】根据 "精细控制" 标志来决定执行流程 ---
        if not use_fine_grained_flow:
            # --- 这是您要求的新默认流程 ---
            log_message(log_callback, "--- 开始执行[流水线]模式：各API独立完成其超级总结 ---", status="INFO", api_id="global")
            
            pipeline_tasks = []
            for api_config in active_api_configs:
                api_id = api_config['id']
                chapters_for_this_api = chapter_distribution.get(api_id, [])
                if chapters_for_this_api:
                    task = asyncio.create_task(_run_full_pipeline_for_api(
                        api_config, chapters_for_this_api, novel_folder_path, prompts,
                        log_callback, pause_event, state_manager, word_counts, summary_batch_size, big_summary_batch_size
                    ))
                    pipeline_tasks.append(task)
            
            if pipeline_tasks:
                results = await asyncio.gather(*pipeline_tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, asyncio.CancelledError):
                        log_message(log_callback, "一个流水线处理任务被取消。", status="INFO", api_id="global")
                        raise asyncio.CancelledError
                    elif isinstance(res, Exception):
                        raise res

            log_message(log_callback, "--- 所有API的独立流程（包括超级总结）均已完成。 ---", status="SUCCESS", api_id="global")

        else:
            # --- 这是保持不变的"精细控制"流程 ---
            log_message(log_callback, "--- 开始执行[精细控制]模式：等待所有大总结完成后再统一处理 ---", status="INFO", api_id="global")
            
            # 1. 先像以前一样，只完成小结和大结
            pipeline_tasks = []
            for api_config in active_api_configs:
                api_id = api_config['id']
                chapters_for_this_api = chapter_distribution.get(api_id, [])
                if chapters_for_this_api:
                    task = asyncio.create_task(_run_small_and_big_summary_for_api(
                        api_config, chapters_for_this_api, novel_folder_path, prompts,
                        log_callback, pause_event, state_manager, word_counts, summary_batch_size, big_summary_batch_size
                    ))
                    pipeline_tasks.append(task)
            
            if pipeline_tasks:
                results = await asyncio.gather(*pipeline_tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, asyncio.CancelledError):
                        log_message(log_callback, "一个处理任务被取消。", status="INFO", api_id="global")
                        raise asyncio.CancelledError
                    elif isinstance(res, Exception):
                        raise res

            log_message(log_callback, "--- [精细控制] 所有API的小结/大结阶段均已完成。 ---", status="SUCCESS", api_id="global")
            
            # 2. 然后再调用自动化的超级总结阶段
            await check_pause_async(pause_event)
            log_message(log_callback, "--- 开始执行[自动分批]超级总结流程 ---", status="INFO", api_id="global")
            await run_automated_super_summary_stage(
                active_api_configs=active_api_configs,
                novel_folder_path=novel_folder_path,
                prompts=prompts,
                word_counts=word_counts,
                log_callback=log_callback,
                pause_event=pause_event,
                state_manager=state_manager,
                super_summary_threshold=super_summary_threshold
            )
        
        await check_pause_async(pause_event)

        # --- 阶段 3 & 4: 超级总结 和 终极总结 ---
        # 经过上面的if/else，到这里时，所有超级总结应该都已完成
        log_message(log_callback, "--- 所有超级总结阶段均已完成。 ---", status="SUCCESS", api_id="global")
        await check_pause_async(pause_event)

        # --- 终极总结 ---
        if not state_manager.is_ultimate_summary_stage_complete():
            ultimate_api_config = next((ac for ac in active_api_configs if ac['id'] == ultimate_api_id), None)
            if not ultimate_api_config:
                log_message(log_callback, f"错误：找不到为终极总结指定的API (ID: {ultimate_api_id})。", status="FAIL", api_id="global")
                return False
            
            log_message(log_callback, f"--- 开始终极总结阶段，由API '{ultimate_api_config.get('api_key_name', ultimate_api_id)}' 执行 ---", status="INFO", api_id="global")
            await run_ultimate_summary_stage(
                ultimate_api_config, novel_folder_path, prompts, word_counts,
                log_callback, pause_event, state_manager
            )
        else:
            log_message(log_callback, "终极总结阶段已全部完成，跳过。", status="INFO", api_id="global")

        log_message(log_callback, "--- 所有总结阶段均已完成。 ---", status="SUCCESS", api_id="global")
        return True

    except asyncio.CancelledError:
        # 当任务被取消时，记录一条信息并返回 False
        log_message(log_callback, "主协调器任务被取消。", status="INFO", api_id="global")
        return False
    except Exception as e:
        # 捕获其他所有未预料到的异常
        tb_info = traceback.format_exc()
        log_message(log_callback, f"主协调器在执行期间发生未知严重错误: {e}", status="FAIL", traceback_info=tb_info)
        return False 
