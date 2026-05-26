# logic/utils.py

"""
This module contains various utility functions used by the logic modules.
"""
import re
import os
import time
import json
import asyncio
from config import TASK_ID_FILENAME
import aiofiles
from typing import Any, Dict, List, Optional
from logic.batching import (
    _distribute_batches_sequentially,
    _distribute_chapters_sequentially,
    build_small_summary_batches,
    small_summary_batch_task_name,
)
from logic.chapter_naming import (
    chinese_to_arabic,
    clean_filename_for_splitting,
    extract_numbers_from_filename,
    get_big_summary_sort_key,
    get_chapter_range_from_filename,
    get_super_ultimate_summary_sort_key,
    natural_sort_key,
    sanitize_api_name,
    sanitize_filename,
)
from logic.summary_outputs import (
    find_existing_summary_output_file,
    is_summary_output_filename,
    normalize_summary_output_format,
    summary_output_filename,
    summary_output_path,
    summary_output_peer_exists,
)
from logic.file_io import (
    _get_token_count,
    read_file_content_robustly,
    read_file_content_robustly_async,
    read_files_and_join,
)
from logic.progress_events import (
    StageProgressTracker,
    check_pause_async,
    emit_stage_progress,
    log_message,
)
from logic.prompt_runtime import (
    get_global_prompt_cache_dir,
    get_summarizer_cache_dir,
    load_all_prompts_for_run as _load_all_prompts_for_run,
)
from logic.text_extraction import (
    extract_character_content,
    extract_character_info_from_summary,
    extract_summary_content,
    extract_tag_content,
)

# --- Logging and Thread Control ---

def load_all_prompts_for_run():
    return _load_all_prompts_for_run(cache_dir=get_global_prompt_cache_dir())


# --- 为实现精确断点续传和调试的结构化API日志 ---

# 使用一个字典来为每个日志文件维护一个异步锁
_api_log_locks = {}
_api_log_locks_lock = asyncio.Lock()

async def _get_api_log_lock(filepath):
    """为每个API日志文件获取或创建一个唯一的异步锁。"""
    async with _api_log_locks_lock:
        if filepath not in _api_log_locks:
            _api_log_locks[filepath] = asyncio.Lock()
        return _api_log_locks[filepath]

def get_api_log_filepath(novel_folder_path, api_id):
    """获取指定API的日志文件路径。"""
    cache_dir = get_summarizer_cache_dir(novel_folder_path)
    # 使用唯一的、经过清理的api_id作为文件名
    safe_api_id = re.sub(r'[^a-zA-Z0-9_-]', '_', api_id)
    return os.path.join(cache_dir, f"api_log_{safe_api_id}.jsonl")

def get_api_failure_log_dir(novel_folder_path):
    """获取API失败诊断日志目录。"""
    return os.path.join(get_summarizer_cache_dir(novel_folder_path), "api_failures")

def _redact_log_value(value: Any):
    if isinstance(value, dict):
        redacted = {}
        sensitive_keys = {
            "key",
            "api_key",
            "authorization",
            "token",
            "access_token",
            "secret",
            "password",
            "credential",
            "credentials",
            "x_api_key",
        }
        for key, item in value.items():
            key_text = str(key)
            key_lower = re.sub(r"[^a-z0-9]+", "_", key_text.lower()).strip("_")
            if (
                key_lower in sensitive_keys
                or key_lower.endswith("_token")
                or key_lower.endswith("_secret")
                or key_lower.endswith("_password")
                or key_lower.endswith("_api_key")
                or key_lower.endswith("_authorization")
            ):
                redacted[key_text] = "[REDACTED]"
            else:
                redacted[key_text] = _redact_log_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_log_value(item) for item in value]
    return value

async def log_api_failure_to_file(novel_folder_path, api_id, task_info):
    """将单次API失败诊断写入独立、格式化的JSON文件。"""
    failure_dir = get_api_failure_log_dir(novel_folder_path)
    safe_api_id = sanitize_api_name(str(api_id))
    timestamp_ms = int(float(task_info.get("timestamp", time.time())) * 1000)
    stage = sanitize_api_name(str(task_info.get("stage") or "unknown_stage"))
    attempt = str(task_info.get("attempt") or "unknown_attempt")
    filename = f"{timestamp_ms}_{safe_api_id}_{stage}_attempt_{attempt}.json"
    filepath = os.path.join(failure_dir, filename)
    lock = await _get_api_log_lock(filepath)

    async with lock:
        try:
            if not await asyncio.to_thread(os.path.exists, failure_dir):
                await asyncio.to_thread(os.makedirs, failure_dir, exist_ok=True)
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                log_entry = json.dumps(_redact_log_value(task_info), ensure_ascii=False, indent=2)
                await f.write(log_entry + '\n')
        except Exception as e:
            print(f"CRITICAL WARNING: Failed to write API failure log {filepath}. Error: {e}")

def cleanup_api_failure_logs(
    novel_folder_path,
    *,
    max_age_days: Optional[float] = None,
    max_files: Optional[int] = None,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Remove old API failure diagnostic JSON files without changing new log writes."""
    if max_age_days is not None and max_age_days < 0:
        raise ValueError("max_age_days must be greater than or equal to 0")
    if max_files is not None and max_files < 0:
        raise ValueError("max_files must be greater than or equal to 0")

    failure_dir = get_api_failure_log_dir(novel_folder_path)
    if not os.path.isdir(failure_dir):
        return {
            "failure_dir": failure_dir,
            "deleted_count": 0,
            "deleted_files": [],
            "kept_count": 0,
        }

    current_time = time.time() if now is None else float(now)
    cutoff = None
    if max_age_days is not None:
        cutoff = current_time - (float(max_age_days) * 86400)

    files = [
        os.path.join(failure_dir, name)
        for name in os.listdir(failure_dir)
        if name.lower().endswith(".json") and os.path.isfile(os.path.join(failure_dir, name))
    ]
    deleted_files: List[str] = []

    def _remove(path: str) -> None:
        try:
            os.remove(path)
        except FileNotFoundError:
            return
        deleted_files.append(path)

    remaining: List[str] = []
    for path in files:
        if cutoff is not None and os.path.getmtime(path) < cutoff:
            _remove(path)
        else:
            remaining.append(path)

    if max_files is not None and len(remaining) > max_files:
        newest_first = sorted(remaining, key=lambda item: os.path.getmtime(item), reverse=True)
        for path in newest_first[max_files:]:
            _remove(path)
        remaining = newest_first[:max_files]

    return {
        "failure_dir": failure_dir,
        "deleted_count": len(deleted_files),
        "deleted_files": deleted_files,
        "kept_count": len(remaining),
    }

async def log_api_task_to_file(novel_folder_path, api_id, task_info):
    """
    将一个结构化的任务信息异步地记录到特定API的日志文件中。
    使用 .jsonl 格式 (每行一个JSON对象)。

    task_info (dict): 包含任务详情的字典，例如:
        {
            "timestamp": time.time(),
            "stage": "small_summary",
            "status": "start" / "success" / "fail",
            "source_file": "/path/to/chapter1.txt",
            "output_plot_file": "/path/to/plot_summary.txt",
            "output_char_file": "/path/to/char_summary.txt",
            "error_message": "...", (仅在失败时)
            "duration_seconds": 12.3 (仅在成功时)
        }
    """
    if task_info.get("status") == "fail":
        await log_api_failure_to_file(novel_folder_path, api_id, task_info)
        return

    filepath = get_api_log_filepath(novel_folder_path, api_id)
    lock = await _get_api_log_lock(filepath)
    
    async with lock:
        try:
            # 确保目录存在
            dir_path = os.path.dirname(filepath)
            if not await asyncio.to_thread(os.path.exists, dir_path):
                await asyncio.to_thread(os.makedirs, dir_path, exist_ok=True)
            
            # 使用 'a' 模式追加内容，每条日志占一行
            async with aiofiles.open(filepath, 'a', encoding='utf-8') as f:
                log_entry = json.dumps(task_info, ensure_ascii=False)
                await f.write(log_entry + '\n')

        except Exception as e:
            # 这是一个关键功能，如果日志记录失败，我们应该在主控制台打印一个非常明显的警告
            print(f"CRITICAL WARNING: Failed to write to API log file {filepath}. "
                  f"Resumability may be compromised. Error: {e}")


# --- Chapter Splitting Shared Logic ---

def _match_group(match, index: int) -> str:
    try:
        return match.group(index) or ""
    except IndexError:
        return ""

def write_chapters_to_file_numeric(output_dir, content_buffer, first_title, last_title, extractor_regex, log_func, chapter_offset=0):
    """
    辅助函数，用于将缓冲区的章节内容写入文件。
    使用更精确的正则表达式来生成文件名。
    新增 chapter_offset 参数以支持分卷。
    """
    first_match = extractor_regex.search(first_title)
    last_match = extractor_regex.search(last_title)

    filename = ""
    # 只有当起始和结束标题都成功匹配到章节号时，才使用数字格式命名
    if first_match and last_match:
        # 【修复】统一从 group(2) 或 group(3) 中提取数字字符串
        first_num_str = (_match_group(first_match, 2) or _match_group(first_match, 3)).strip()
        last_num_str = (_match_group(last_match, 2) or _match_group(last_match, 3)).strip()

        # 【恢复】增加了对提取失败的严格检查
        if not first_num_str or not last_num_str:
            log_func(f"严重错误: 正则表达式在标题 '{first_title}' 或 '{last_title}' 上匹配成功，但无法找到章节编号。请检查你的自定义规律。", status='FAIL')
            # 使用备用方案创建文件名，以避免丢失数据，但日志中已标记为严重错误
            filename = f"{clean_filename_for_splitting(first_title)}-{clean_filename_for_splitting(last_title)}.txt"
        else:
            try:
                first_num_local = chinese_to_arabic(first_num_str)
                last_num_local = chinese_to_arabic(last_num_str)

                # 应用全局偏移量
                global_first_num = first_num_local + chapter_offset
                global_last_num = last_num_local + chapter_offset

                if global_first_num == global_last_num:
                    filename = f"第{global_first_num:03d}章.txt"
                else:
                    filename = f"第{global_first_num:03d}章-第{global_last_num:03d}章.txt"
            except (ValueError, IndexError):
                # 如果中文转数字失败，则记录警告并使用备用方案
                log_func(f"警告: 无法从数字字符串 '{first_num_str}' 或 '{last_num_str}' 中解析章节号，将使用标题文本。", status='WARN')
                filename = f"{clean_filename_for_splitting(first_title)}-{clean_filename_for_splitting(last_title)}.txt"

    else:
        # 如果匹配失败，则使用清理后的标题作为备用方案
        log_func(f"警告: 无法从标题 '{first_title}' 或 '{last_title}' 中精确提取章节号，将使用标题文本生成文件名。", status='WARN')
        filename = f"{clean_filename_for_splitting(first_title)}-{clean_filename_for_splitting(last_title)}.txt"

    safe_filename = clean_filename_for_splitting(filename)
    output_path = os.path.join(output_dir, safe_filename)
    
    with open(output_path, 'w', encoding='utf-8') as out_f:
        out_f.write(content_buffer)
    log_func(f"已生成文件: {safe_filename}")

def process_chapters_with_regex(
    content, output_directory_path, handle_volumes, log_callback, chapter_pattern
):
    """
    一个共享的处理函数，它使用给定的正则表达式来分割、缓冲和写入章节。
    【已重构】修复了章节切分和缓冲逻辑的根本性错误。
    """
    def _log(message, status=None):
        log_callback(message)

    matches = list(chapter_pattern.finditer(content))
    if not matches:
        _log(f"错误：在文件中未能找到任何符合规律 '{chapter_pattern.pattern}' 的章节标题。")
        return False, 0

    _log(f"初步找到 {len(matches)} 个章节。")
    chapters_per_output = 1
    os.makedirs(output_directory_path, exist_ok=True)

    file_count = 0
    chapters_in_buffer = 0
    content_buffer = ""
    first_title_in_buffer = ""
    
    last_processed_local_num = 0
    volume_offset = 0

    for i, match in enumerate(matches):
        current_title = match.group(1).strip()
        
        start_pos = match.start()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        current_content = content[start_pos:end_pos]

        # --- 分卷处理逻辑 (保持不变) ---
        current_local_num = -1
        if handle_volumes:
            title_match_for_volume = chapter_pattern.search(current_title)
            if title_match_for_volume:
                try:
                    num_str = title_match_for_volume.group(2).strip()
                    current_local_num = chinese_to_arabic(num_str)
                except (IndexError, ValueError):
                    pass
            
            if current_local_num != -1 and 0 < current_local_num < last_processed_local_num:
                _log(f"检测到章节号重置（可能进入新的一卷）: 从 {last_processed_local_num} 到 {current_local_num}。")
                if content_buffer:
                    # 写入分卷前的剩余章节
                    last_title_before_volume_change = matches[i-1].group(1).strip()
                    write_chapters_to_file_numeric(
                        output_directory_path, content_buffer, first_title_in_buffer,
                        last_title_before_volume_change, chapter_pattern, _log, volume_offset
                    )
                    file_count += 1
                    content_buffer = ""
                    chapters_in_buffer = 0

                volume_offset += last_processed_local_num
                _log(f"更新全局章节偏移为: {volume_offset}")
            
            if current_local_num != -1:
                last_processed_local_num = current_local_num
        # --- 分卷处理逻辑结束 ---

        if chapters_in_buffer == 0:
            first_title_in_buffer = current_title

        content_buffer += current_content
        chapters_in_buffer += 1

        if chapters_in_buffer >= chapters_per_output:
            write_chapters_to_file_numeric(
                output_directory_path, content_buffer.strip(), first_title_in_buffer,
                current_title, chapter_pattern, _log, volume_offset
            )
            file_count += 1
            content_buffer = ""
            chapters_in_buffer = 0
            first_title_in_buffer = ""

    # 处理循环结束后剩余的章节
    if content_buffer:
        last_title = matches[-1].group(1).strip()
        write_chapters_to_file_numeric(
            output_directory_path, content_buffer.strip(), first_title_in_buffer,
            last_title, chapter_pattern, _log, volume_offset
        )
        file_count += 1

    _log(f"处理完成，总共生成了 {file_count} 个文件。")
    return True, file_count


def get_final_summary_path(root_dir, summary_type, api_display_name="final"):
    """
    为最终的大总结文件生成一个标准化的路径。
    summary_type 应该是 'plot' 或 'char'。
    """
    return os.path.join(root_dir, f"{summary_type}_{api_display_name}_summary.txt")

def find_and_sort_chapter_files(directory, log_callback):
    """
    在指定目录中查找并排序章节文件。
    - 使用多种策略来解析章节号，以实现最大的兼容性。
    - 自动排除非章节的 'task_id.txt' 文件。
    - 返回一个有序的章节文件名列表。
    """
    if not os.path.isdir(directory):
        log_callback(f"错误：提供的路径 '{directory}' 不是一个有效的目录。", "ERROR")
        return []

    try:
        all_files = [f for f in os.listdir(directory) if f.endswith('.txt')]
    except OSError as e:
        log_callback(f"错误：无法读取目录 '{directory}': {e}", "ERROR")
        return []

    # 排除 task_id.txt
    if TASK_ID_FILENAME in all_files:
        all_files.remove(TASK_ID_FILENAME)
        log_callback(f"已自动排除状态文件 '{TASK_ID_FILENAME}'。", "INFO")

    if not all_files:
        log_callback("警告：在指定目录中没有找到 .txt 文件。", "WARN")
        return []

    # 使用 natural_sort_key 对文件名进行排序
    sorted_files = sorted(all_files, key=natural_sort_key)
    
    # 返回文件的完整路径
    full_path_files = [os.path.join(directory, f) for f in sorted_files] 
    
    log_callback(f"成功找到并排序了 {len(full_path_files)} 个章节文件。", "INFO")
    return full_path_files

