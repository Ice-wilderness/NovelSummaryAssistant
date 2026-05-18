# python/splitters/regex_strategy.py

import os
import re
# 从 utils 导入共享的处理器
from python.logic.utils import process_chapters_with_regex

def run(content, output_directory_path, chapters_per_file, handle_volumes, log_callback, custom_pattern):
    """
    Splits a novel by chapters based on a user-defined regex pattern.
    """
    log_callback("正在使用自定义规律策略进行分割...")

    if not custom_pattern or 'n' not in custom_pattern.lower():
        log_callback("错误：自定义规律不能为空，且必须包含 'n' 或 'N' 来代表章节号。")
        return False, 0

    # 采用更健壮的正则构建逻辑，以 'n' 分割并自动处理空格
    parts = re.split('(n)', custom_pattern, flags=re.IGNORECASE)
    prefix = re.escape(parts[0])
    suffix = re.escape(parts[2]) if len(parts) > 2 else ''
    
    number_regex_part = r'([一二三四五六七八九十百千万亿零\d]+)'
    
    # 构建灵活的、能处理各种空格情况的用户模式正则
    user_chapter_regex = fr"{prefix}\s*{number_regex_part}\s*{suffix}"
    
    # 【修复】根据 handle_volumes 标志决定最终的正则表达式
    if handle_volumes:
        log_callback("分卷处理已启用，将同时匹配卷标题。")
        # 分卷模式的正则表达式
        volume_regex = r'第\s*[一二三四五六七八九十百千万亿零\d]+\s*[卷部]'
        # 组合用户模式和分卷模式
        combined_regex = fr"(?:{user_chapter_regex}|{volume_regex})"
    else:
        # 仅使用用户模式
        combined_regex = user_chapter_regex

    # 最终的正则表达式结构:
    # group(1): 捕获包含标题的完整行
    final_pattern_str = fr"({combined_regex}\s*.*)"

    chapter_pattern = re.compile(fr'^\s*{final_pattern_str}', re.MULTILINE | re.IGNORECASE)
    
    log_callback(f"生成的正则表达式: {chapter_pattern.pattern}")

    # 调用共享的处理函数
    success, file_count = process_chapters_with_regex(
        content=content,
        output_directory_path=output_directory_path,
        chapters_per_file=chapters_per_file,
        handle_volumes=handle_volumes,
        log_callback=log_callback,
        chapter_pattern=chapter_pattern
    )
    
    if success:
        log_callback(f"自定义规律策略分割完成，总共生成了 {file_count} 个文件。")
        
    return success, file_count 
