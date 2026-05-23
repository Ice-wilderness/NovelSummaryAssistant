# logic/chapter_splitter.py

import os
import re
import chardet
import traceback
from tkinter import messagebox
import logging
from logic.utils import chinese_to_arabic, read_file_content_robustly
from splitters import default_strategy, regex_strategy, title_list_strategy

# 文本处理与章节分割辅助函数

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read(32768) # Read a chunk of the file
    return chardet.detect(raw_data)['encoding']

def clean_filename_for_splitting(title):
    # Keep Chinese characters, numbers, basic English letters, and dots.
    # Remove most special characters that are problematic for filenames.
    cleaned_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s.-]', '', title).strip()
    # Replace spaces with underscores
    cleaned_title = cleaned_title.replace(' ', '_')
    return cleaned_title if cleaned_title else "untitled_chapter"


def split_novel_into_chapter_files(
    source_txt_file_path,
    output_directory_path,
    handle_volumes=False,
    log_callback=None,
    mode="default",
    custom_pattern=None,
    title_list=None,
    pattern_config=None,
):
    """
    Dispatcher function that reads a source file and calls the appropriate
    splitting strategy based on the selected mode.
    """

    def _log(message):
        if log_callback:
            log_callback(f"[调度器]: {message}", api_id="global")
        else:
            print(f"[调度器]: {message}")

    try:
        _log(f"开始处理源文件: {source_txt_file_path}")
        content = read_file_content_robustly(source_txt_file_path)
        _log("文件读取完成，正在根据模式调用相应策略...")

        if mode == "default":
            return default_strategy.run(
                content=content,
                output_directory_path=output_directory_path,
                handle_volumes=handle_volumes,
                log_callback=log_callback
            )
        elif mode == "regex":
            # 优先使用 pattern_config（raw 模式完整正则）
            if pattern_config is not None and getattr(pattern_config, "regex_mode", None) == "raw":
                return regex_strategy.run_with_raw_regex(
                    content=content,
                    output_directory_path=output_directory_path,
                    handle_volumes=handle_volumes,
                    log_callback=log_callback,
                    raw_pattern_str=pattern_config.pattern,
                )
            if custom_pattern:
                return regex_strategy.run(
                    content=content,
                    output_directory_path=output_directory_path,
                    handle_volumes=handle_volumes,
                    log_callback=log_callback,
                    custom_pattern=custom_pattern,
                )
            _log("错误: '自定义规律'模式需要提供 custom_pattern 或 pattern_config 参数。")
            return False, 0
        elif mode == "title_list":
            if not title_list:
                _log("错误: '全定义标题'模式需要提供 title_list 参数。")
                return False, 0
            return title_list_strategy.run(
                content=content,
                output_directory_path=output_directory_path,
                log_callback=log_callback,
                title_list=title_list
            )
        else:
            _log(f"错误: 未知的分割模式 '{mode}'。")
            return False, 0

    except Exception as e:
        _log(f"章节分割过程中发生严重错误: {e}")
        _log(traceback.format_exc())
        return False, 0


def _write_buffered_chapters_to_file(output_dir, content_buffer, first_title, last_title, extractor_regex, log_func, chapter_offset=0):
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
        first_num_str = first_match.group(2).strip()
        last_num_str = last_match.group(2).strip()
        first_num_local = chinese_to_arabic(first_num_str)
        last_num_local = chinese_to_arabic(last_num_str)

        # 应用全局偏移量
        global_first_num = first_num_local + chapter_offset
        global_last_num = last_num_local + chapter_offset

        filename = f"第{global_first_num}章-第{global_last_num}章.txt"
    else:
        # 如果匹配失败，则使用清理后的标题作为备用方案
        log_func(f"警告: 无法从标题 '{first_title}' 或 '{last_title}' 中精确提取章节号，将使用标题文本生成文件名。")
        filename = f"{clean_filename_for_splitting(first_title)}-{clean_filename_for_splitting(last_title)}.txt"

    safe_filename = clean_filename_for_splitting(filename)
    output_path = os.path.join(output_dir, safe_filename)
    
    with open(output_path, 'w', encoding='utf-8') as out_f:
        out_f.write(content_buffer)
    log_func(f"已生成文件: {safe_filename}")

# ── 预览功能 ─────────────────────────────────────────────────

DEFAULT_PREVIEW_PATTERN = re.compile(
    r'^\s*((第\s*[一二三四五六七八九十百千万亿零\d]+\s*(?:章|节|回)).*)',
    re.MULTILINE,
)


def _count_line_number(content: str, pos: int) -> int:
    """计算指定字符位置对应的行号（1-based）。"""
    return content[:pos].count('\n') + 1


def preview_split(
    content: str,
    mode: str = "default",
    pattern_config: "PatternConfig | None" = None,
    title_list: list | None = None,
    handle_volumes: bool = True,
) -> list:
    """扫描源文本，返回匹配到的章节列表（不写入任何文件）。

    返回格式: [{"index": 1, "title": "第一章 xxx", "line_number": 42}, ...]
    """
    if not content.strip():
        return []

    if mode == "default":
        return _preview_with_pattern(content, DEFAULT_PREVIEW_PATTERN)
    elif mode == "regex":
        if pattern_config is None:
            raise ValueError("正则模式需要提供 pattern_config")
        from webui_backend.pattern_config_service import PatternConfigService
        from splitters.regex_strategy import compile_raw_pattern, build_regex_from_simple_pattern

        if pattern_config.regex_mode == "simple":
            pattern_str = build_regex_from_simple_pattern(pattern_config.pattern)
        else:
            pattern_str = PatternConfigService._wrap_raw_if_needed(pattern_config.pattern)

        compiled = re.compile(pattern_str, re.MULTILINE | re.IGNORECASE)
        return _preview_with_pattern(content, compiled)
    elif mode == "title_list":
        if not title_list:
            raise ValueError("标题列表模式需要提供 title_list")
        return _preview_with_title_list(content, title_list)
    else:
        raise ValueError(f"未知的分割模式: {mode}")


def _preview_with_pattern(content: str, pattern: re.Pattern) -> list:
    """用正则模式扫描内容，返回章节预览列表（含字数）。"""
    results = []
    matches = list(pattern.finditer(content))
    for i, match in enumerate(matches):
        title = match.group(1).strip() if match.lastindex and match.lastindex >= 1 else match.group(0).strip()
        line_number = _count_line_number(content, match.start())
        # 章节内容从当前匹配到下一个匹配（或文末）
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        word_count = end - match.start()
        results.append({
            "index": i + 1,
            "title": title,
            "line_number": line_number,
            "word_count": word_count,
        })
    return results


def _preview_with_title_list(content: str, titles: list) -> list:
    """按标题列表顺序扫描内容，返回章节预览列表（含字数）。"""
    results = []
    # 先找到所有标题位置
    escaped_titles = [re.escape(t.strip()) for t in titles if t.strip()]
    pattern_str = '|'.join(escaped_titles)
    chapter_pattern = re.compile(f'^\\s*({pattern_str})\\s*$', re.MULTILINE)
    matches = list(chapter_pattern.finditer(content))

    for index, title in enumerate(titles, start=1):
        stripped = title.strip()
        match = next((m for m in matches if m.group(1).strip() == stripped), None)
        if match:
            line_number = _count_line_number(content, match.start())
            # 在 matches 中找到当前位置
            match_idx = matches.index(match)
            end = matches[match_idx + 1].start() if match_idx + 1 < len(matches) else len(content)
            word_count = end - match.start()
            results.append({
                "index": index,
                "title": stripped,
                "line_number": line_number,
                "word_count": word_count,
                "matched": True,
            })
        else:
            results.append({
                "index": index,
                "title": stripped,
                "line_number": 0,
                "word_count": 0,
                "matched": False,
            })
    return results


# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
