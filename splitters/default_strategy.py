# splitters/default_strategy.py

import os
import re
# 从 utils 导入共享的处理器
from logic.utils import process_chapters_with_regex

def run(content, output_directory_path, handle_volumes, log_callback):
    """
    Default strategy for splitting a novel by chapters based on a fixed regex pattern.
    """
    log_callback("正在使用默认策略进行分割...")

    # 默认的正则表达式，用于匹配 "第 X 章/节/回..." 等格式
    # 捕获组1: 完整的章节标题 (例如, "第 一百二十三 章")
    # 捕获组2: 章节号本身 (例如, "一百二十三")
    chapter_pattern = re.compile(
        r'^\s*((第\s*[一二三四五六七八九十百千万亿零\d]+\s*(?:章|节|回)).*)',
        re.MULTILINE
    )

    # 调用共享的处理函数
    success, file_count = process_chapters_with_regex(
        content=content,
        output_directory_path=output_directory_path,
        handle_volumes=handle_volumes,
        log_callback=log_callback,
        chapter_pattern=chapter_pattern
    )

    if success:
        log_callback(f"默认策略分割完成，总共生成了 {file_count} 个文件。")
    
    return success, file_count 
