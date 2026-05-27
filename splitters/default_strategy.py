# splitters/default_strategy.py

# 从 utils 导入共享的处理器
from logic.chapter_boundaries import DEFAULT_CHAPTER_PATTERN
from logic.utils import process_chapters_with_regex

def run(content, output_directory_path, handle_volumes, log_callback):
    """
    Default strategy for splitting a novel by chapters based on a fixed regex pattern.
    """
    log_callback("正在使用默认策略进行分割...")

    # 调用共享的处理函数
    success, file_count = process_chapters_with_regex(
        content=content,
        output_directory_path=output_directory_path,
        handle_volumes=handle_volumes,
        log_callback=log_callback,
        chapter_pattern=DEFAULT_CHAPTER_PATTERN
    )

    if success:
        log_callback(f"默认策略分割完成，总共生成了 {file_count} 个文件。")
    
    return success, file_count 
