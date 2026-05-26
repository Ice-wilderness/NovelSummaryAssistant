import asyncio
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import aiofiles

from logic.chapter_naming import sanitize_api_name
from logic.prompt_runtime import get_summarizer_cache_dir


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
