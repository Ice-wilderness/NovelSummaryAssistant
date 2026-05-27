# splitters/title_list_strategy.py

from logic.chapter_boundaries import title_list_boundaries
from logic.chapter_writing import write_title_boundaries_to_files

def run(content, output_directory_path, log_callback, title_list):
    """
    Splits a novel into multiple files based on a user-provided list of exact chapter titles.
    Each part is defined as the content between two titles, or before the first/after the last title.
    """
    log_callback("正在使用'全定义标题'策略进行分割...")
    log_callback("此模式将按标题列表固定输出单章文件。")

    if not title_list:
        log_callback("错误：标题列表为空。")
        return False, 0
    
    boundaries = title_list_boundaries(content, title_list)
    log_callback(f"使用 {len([item for item in boundaries if item.matched])} 个标题生成分割规则...")
    return write_title_boundaries_to_files(content, output_directory_path, boundaries, log_callback)
