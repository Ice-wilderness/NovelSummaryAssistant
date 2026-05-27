# splitters/regex_strategy.py

import re
from logic.chapter_boundaries import (
    build_regex_from_simple_pattern as _build_regex_from_simple_pattern,
    compile_raw_pattern as _compile_raw_pattern,
)
from logic.utils import process_chapters_with_regex


def build_regex_from_simple_pattern(custom_pattern: str) -> str:
    """将含 `n` 占位符的简化模式构建为完整正则字符串。

    例如 `第n章` 构建为 `第\\s*([一二三四五六七八九十百千万亿零\\d]+)\\s*章`，
    然后包裹为满足 group(1)/group(2) 约定的格式。
    """
    return _build_regex_from_simple_pattern(custom_pattern)


def compile_raw_pattern(raw_pattern: str, sample_text: str = "") -> re.Pattern:
    """将 raw 模式的完整正则编译为可用于 chapter matching 的 Pattern。

    若正则会不含捕获组，自动包裹为 ``^\\s*(({pattern}).*)`` 以生成 group(1)/group(2)。
    """
    return _compile_raw_pattern(raw_pattern, sample_text=sample_text)


def run(content, output_directory_path, handle_volumes, log_callback, custom_pattern):
    """
    Splits a novel by chapters based on a user-defined regex pattern (simple mode with `n` placeholder).
    """
    log_callback("正在使用自定义规律策略进行分割...")

    if not custom_pattern or 'n' not in custom_pattern.lower():
        log_callback("错误：自定义规律不能为空，且必须包含 'n' 或 'N' 来代表章节号。")
        return False, 0

    full_pattern = build_regex_from_simple_pattern(custom_pattern)
    chapter_pattern = re.compile(full_pattern, re.MULTILINE | re.IGNORECASE)
    log_callback(f"生成的正则表达式: {chapter_pattern.pattern}")

    return _run_with_pattern(content, output_directory_path, handle_volumes, log_callback, chapter_pattern)


def run_with_raw_regex(content, output_directory_path, handle_volumes, log_callback, raw_pattern_str):
    """使用 raw 模式的完整正则进行分割。"""
    log_callback("正在使用完整正则策略进行分割...")

    if not raw_pattern_str.strip():
        log_callback("错误：正则表达式不能为空。")
        return False, 0

    chapter_pattern = compile_raw_pattern(raw_pattern_str, sample_text=content)
    log_callback(f"编译的正则表达式: {chapter_pattern.pattern}")

    return _run_with_pattern(content, output_directory_path, handle_volumes, log_callback, chapter_pattern)


def _run_with_pattern(content, output_directory_path, handle_volumes, log_callback, chapter_pattern):
    """内部统一入口：使用编译好的 Pattern 调用共享处理器。"""
    success, file_count = process_chapters_with_regex(
        content=content,
        output_directory_path=output_directory_path,
        handle_volumes=handle_volumes,
        log_callback=log_callback,
        chapter_pattern=chapter_pattern,
    )

    if success:
        log_callback(f"正则策略分割完成，总共生成了 {file_count} 个文件。")

    return success, file_count
