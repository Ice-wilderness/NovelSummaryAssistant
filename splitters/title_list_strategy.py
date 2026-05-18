# splitters/title_list_strategy.py

import os
import re
from logic.utils import clean_filename_for_splitting

def _write_chapters_to_file_sequential(output_dir, content_buffer, first_part_num, last_part_num, log_func):
    """
    Helper to write buffered chapters to a file, naming it based on sequential part numbers.
    """
    filename = f"第{first_part_num}部分-第{last_part_num}部分.txt"
    safe_filename = clean_filename_for_splitting(filename)
    output_path = os.path.join(output_dir, safe_filename)

    with open(output_path, 'w', encoding='utf-8') as out_f:
        out_f.write(content_buffer)
    log_func(f"已生成文件: {safe_filename}")

def run(content, output_directory_path, chapters_per_file, log_callback, title_list):
    """
    Splits a novel into multiple files based on a user-provided list of exact chapter titles.
    Each part is defined as the content between two titles, or before the first/after the last title.
    """
    log_callback("正在使用'全定义标题'策略进行分割...")
    log_callback("此模式将忽略'每文件包含章节数'设置，并基于标题进行精确分割。")

    if not title_list:
        log_callback("错误：标题列表为空。")
        return False, 0
    
    # Escape each title to be safe for regex, then join with '|'
    escaped_titles = [re.escape(title.strip()) for title in title_list if title.strip()]
    if not escaped_titles:
        log_callback("错误：处理后的标题列表为空。")
        return False, 0
        
    # Create a regex pattern that captures the titles.
    # The whole pattern is a capturing group to get the matched title.
    pattern_str = '|'.join(escaped_titles)
    chapter_pattern = re.compile(f'^\\s*({pattern_str})\\s*$', re.MULTILINE)

    log_callback(f"使用 {len(escaped_titles)} 个标题生成分割规则...")

    # Use re.split to get alternating content and titles
    parts = chapter_pattern.split(content)

    if len(parts) <= 1:
        log_callback("错误：在文件中未能找到任何提供的标题。请检查标题是否与原文完全一致（包括空格）。")
        return False, 0

    os.makedirs(output_directory_path, exist_ok=True)
    file_counter = 0

    # Part 1: Handle content before the first title (prologue)
    prologue_content = parts[0].strip()
    if prologue_content:
        filename = f"{file_counter:03d}_开头部分.txt"
        output_path = os.path.join(output_directory_path, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(prologue_content)
        log_callback(f"已生成文件: {filename}")
        file_counter += 1

    # Part 2: Handle content between titles and the final part
    # We iterate through the list of titles, which are at odd indices (1, 3, 5...)
    for i in range(1, len(parts), 2):
        # The title is the current part
        title = parts[i].strip()
        
        # The content for this chapter is the part immediately after the title
        content_after_title = parts[i+1].strip() if (i + 1) < len(parts) else ""
        
        # Combine title and its content
        full_chapter_content = title + "\n\n" + content_after_title
        
        # Generate a clean filename from the title, prefixed with a counter for order
        safe_title = clean_filename_for_splitting(title)
        # Limit filename length to avoid OS errors
        safe_title = safe_title[:50]
        filename = f"{file_counter:03d}_{safe_title}.txt"
        output_path = os.path.join(output_directory_path, filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_chapter_content)
        log_callback(f"已生成文件: {filename}")
        file_counter += 1

    log_callback(f"'全定义标题'策略分割完成，总共生成了 {file_counter} 个文件。")
    return True, file_counter 
