# python/gui/ui_components/utils.py

"""
This module contains various utility functions used by the logic modules.
"""
import re
import os
import time
import json
import tiktoken
import asyncio
from python.config import TASK_ID_FILENAME
from python.logic.prompts import DEFAULT_PROMPTS
import aiofiles
from typing import List

# --- Logging and Thread Control ---

def log_message(log_callback, message, api_id=None, is_progress_log=False, progress_text=None, api_display_name=None, traceback_info=None, status=None):
    """
    一个包装器，用于将日志消息排队到GUI。
    - message: 将显示在GUI和控制台中的用户友好消息。
    - traceback_info: (可选) 仅显示在控制台中的详细回溯信息。
    - status: (可选) 日志的状态 ('START', 'SUCCESS', 'WARN', 'FAIL', 'INFO')，用于添加前缀。
    """
    
    status_prefixes = {
        'START': '[开始]',
        'SUCCESS': '[成功]',
        'WARN': '[警告]',
        'FAIL': '[失败]'
    }
    # 这个前缀只用于控制台日志
    prefix = status_prefixes.get(status, '')
    
    full_console_message = f"{prefix} {message}" if prefix else message

    # 1. 将【原始】消息和状态发送到GUI，让GUI来决定如何格式化
    if log_callback:
        log_source_id = api_display_name or api_id or "global"
        
        log_callback(
            source_id=log_source_id,
            message=message,
            is_progress_log=is_progress_log,
            progress_text=progress_text,
            api_id_for_log=log_source_id, # api_id_for_log 和 source_id 在后台逻辑中是相同的
            traceback_info=traceback_info,
            status=status
        )
    
    # 2. 将带前缀的消息打印到控制台
    console_api_name = api_display_name or api_id or 'SYSTEM'
    print(f"[{console_api_name}] {full_console_message}")

    # 3. 如果有回溯信息，也将其打印到控制台
    if traceback_info:
        print(traceback_info)


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


async def check_pause_async(pause_event):
    """
    【重构】只处理暂停逻辑的异步版本。
    停止功能现在通过 asyncio.Task.cancel() 实现。
    """
    if pause_event and pause_event.is_set():
        log_message(print, "任务已暂停，等待 resume...", "SYSTEM_DEBUG")
        # 使用 to_thread 来正确地、非阻塞地等待同步事件
        await asyncio.to_thread(pause_event.wait)
        log_message(print, "任务已恢复。", "SYSTEM_DEBUG")

# --- Filename and Path Utilities ---

def sanitize_filename(filename, max_length=150):
    """
    一个非常健壮的函数，用于清理和规范化文件名，使其在所有主流操作系统上都安全。
    - 移除或替换非法字符。
    - 将文件名截断到安全长度，同时保留文件扩展名。
    - 处理特殊情况和边缘案例。
    """
    if not filename:
        return ""

    # 分离文件名和扩展名
    base, ext = os.path.splitext(filename)

    # 定义非法字符集（涵盖Windows, macOS, Linux）
    # Windows: < > : " / \ | ? *
    # Unix-like (macOS, Linux): / (以及空字符 \0)
    # 虽然其他字符在技术上是允许的，但作为文件名可能引起shell或其他工具的麻烦
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
    
    # 替换非法字符为下划线
    sanitized_base = re.sub(illegal_chars, '_', base)
    
    # 替换掉可能引起问题的其他字符
    sanitized_base = sanitized_base.replace(' ', '_').replace('__', '_')

    # 限制文件名总长度 (base + ext)
    # -5 是为了给未来的后缀（如_api_1）留出空间
    available_length = max_length - len(ext) - 5
    if len(sanitized_base) > available_length:
        # 从中间截断，保留开头和结尾，更有利于识别
        # 保留前60%和后40%（大约）
        keep_front = int(available_length * 0.6)
        keep_back = available_length - keep_front
        sanitized_base = f"{sanitized_base[:keep_front]}...{sanitized_base[-keep_back:]}"

    # 重新组合并确保没有多余的.
    final_filename = f"{sanitized_base}{ext}".strip('.')
    
    # 防止文件名以 "." 或 "-" 开头 (在Unix-like系统中可能被视为隐藏文件或选项)
    if final_filename.startswith(('.', '-')):
        final_filename = '_' + final_filename

    # 最终检查，确保文件名不为空
    if not final_filename:
        # 如果原始文件名全是是非法字符，就返回一个默认值
        import uuid
        return str(uuid.uuid4())

    return final_filename

def sanitize_api_name(api_name: str) -> str:
    """清理API名称，使其适合用作文件名的一部分。"""
    if not api_name:
        return "UnknownAPI"
    # 移除非法字符，并将空格替换为下划线
    sanitized = re.sub(r'[<>:"/\\|?*]', '', api_name)
    sanitized = sanitized.replace(' ', '_')
    return sanitized

def clean_filename_for_splitting(filename):
    """
    Cleans a filename by removing characters that are illegal in Windows filenames.
    """
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def get_global_prompt_cache_dir():
    """
    获取全局提示词缓存目录的绝对路径。
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(project_root, "prompt_cache")

# --- Text and Token Utilities ---

def _get_token_count(text, model_name="gpt-4"):
    """使用tiktoken计算文本中的token数量。"""
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


async def read_file_content_robustly_async(filepath):
    """
    【新增】read_file_content_robustly 的异步版本。
    尝试用多种常见中文编码异步读取文本文件。
    """
    try:
        async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
            return await f.read()
    except UnicodeDecodeError:
        # 如果UTF-8失败，则切换到二进制读取以进行编码检测
        pass
    except Exception as e:
        # 捕获其他可能的IO错误
        print(f"Initial async read with utf-8 failed: {e}")
        pass

    try:
        import chardet
        async with aiofiles.open(filepath, 'rb') as f:
            raw = await f.read()
        detected = chardet.detect(raw)
        enc = detected['encoding']
        if enc:
            try:
                return raw.decode(enc)
            except Exception:
                pass
    except Exception as e:
        print(f"Chardet detection failed: {e}")
        pass
        
    # 尝试其他常见编码
    for enc in ['gbk', 'gb18030']:
        try:
            async with aiofiles.open(filepath, 'r', encoding=enc) as f:
                return await f.read()
        except Exception:
            continue
            
    raise UnicodeDecodeError(f"无法使用所有备用编码异步读取文件: {filepath}")


def read_file_content_robustly(filepath):
    """
    尝试用多种常见中文编码读取文本文件，保证最大兼容性。
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        pass
    try:
        import chardet
        with open(filepath, 'rb') as f:
            raw = f.read()
        detected = chardet.detect(raw)
        enc = detected['encoding']
        if enc:
            try:
                return raw.decode(enc)
            except Exception:
                pass
    except Exception:
        pass
    for enc in ['gbk', 'gb18030']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except Exception:
            continue
    raise UnicodeDecodeError(f"无法识别文件编码: {filepath}")

def extract_character_info_from_summary(summary_text):
    """
    根据 <character_info_block_start/end> 标签从总结文本中提取角色信息块。
    此函数能容忍标签中的大小写和多余空格，并能在闭合标签缺失时进行回退。
    """
    # 主模式：寻找被完整标签包裹的块。
    # re.DOTALL 让 '.' 可以匹配换行符，re.IGNORECASE 忽略大小写。
    # '.*?' 是非贪婪匹配，确保只匹配到第一个闭合标签。
    pattern = re.compile(
        r"<\s*character_info_block_start\s*>.*?<\s*/\s*character_info_block_end\s*>",
        re.DOTALL | re.IGNORECASE
    )
    
    match = pattern.search(summary_text)
    
    if match:
        # match.group(0) 返回整个匹配到的字符串（即标签+内容）
        return match.group(0).strip()
        
    # 回退模式：如果只找到了开始标签但没有找到闭合标签。
    # 这模仿了旧版逻辑的健壮性，即从一个已知的点匹配到结尾。
    pattern_start_only = re.compile(
        r"<\s*character_info_block_start\s*>.*",
        re.DOTALL | re.IGNORECASE
    )
    match_start_only = pattern_start_only.search(summary_text)
    if match_start_only:
        return match_start_only.group(0).strip()
        
    # 如果两种模式都未匹配，则返回空字符串。
    return ""


# --- Number Conversion Utilities ---

_CH_NUM_MAP = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '两': 2}
_CH_UNIT_MAP = {'十': 10, '百': 100, '千': 1000}
_CH_SECTION_UNIT_MAP = {'万': 10000, '亿': 100000000, '兆': 1000000000000}

_EN_NUM_MAP = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 
    'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20
}

def chinese_to_arabic(cn_str):
    """
    一个健壮的函数，将包含中文数字的字符串转换为阿拉伯数字。
    """
    if not cn_str or not isinstance(cn_str, str): 
        return 0
    cn_str = cn_str.strip()
    if not cn_str: 
        return 0
    if cn_str.isdigit(): 
        return int(cn_str)
    if cn_str == '十': 
        return 10
    res, section_val, current_digit_val = 0, 0, 0
    if len(cn_str) > 1 and cn_str[0] == '一' and cn_str[1] in _CH_UNIT_MAP and _CH_UNIT_MAP[cn_str[1]] == 10:
        cn_str = cn_str[1:]
    for char_cn in cn_str:
        if char_cn in _CH_NUM_MAP:
            current_digit_val = _CH_NUM_MAP[char_cn]
        elif char_cn in _CH_UNIT_MAP:
            unit = _CH_UNIT_MAP[char_cn]
            if current_digit_val == 0 and section_val == 0 and unit == 10:
                current_digit_val = 1
            section_val += current_digit_val * unit
            current_digit_val = 0
        elif char_cn in _CH_SECTION_UNIT_MAP:
            section_unit = _CH_SECTION_UNIT_MAP[char_cn]
            res += (section_val + current_digit_val) * section_unit
            section_val, current_digit_val = 0, 0
        elif char_cn.isdigit():
             pass 
        else:
            pass
    res += section_val + current_digit_val
    return res

def get_chapter_range_from_filename(filename):
    """
    从各种格式的文件名中提取起始章节号，用于排序。
    【已增强】增加了更多匹配模式，使其更加健壮。
    """
    basename = os.path.basename(filename)
    # 定义一个更全面的正则表达式列表
    patterns = [
        # 【新】模式0: 优先匹配 "数字#数字" 格式，并提取第一个数字
        re.compile(r'^(\d+)#\d+'),
        # 模式1: 匹配 "第 1 章", "第一章", "第1话", "第一回" 等
        re.compile(r'第\s*([一二三四五六七八九十百千万亿零\d]+)\s*[章話回]', re.IGNORECASE),
        # 模式2: 匹配 "第 1 -", "第一–"
        re.compile(r'第\s*([一二三四五六七八九十百千万亿零\d]+)\s*[-–—]', re.IGNORECASE),
        # 模式3: 匹配 "ch.1", "chapter 1", "ep 1", "#1", "episode 1" 等在开头的格式
        re.compile(r'^(?:ch|chapter|ep|#|episode)?\s*\.?\s*(\d+)', re.IGNORECASE),
        # 模式4: 匹配 (1), [1], "1." 等在开头的格式
        re.compile(r'^[\[\(]?\s*(\d+)\s*[\]\)\.]'),
        # 模式5: 匹配一个孤立的数字，前后有空格或特殊字符，避免匹配到文件名中的大串随机数字
        re.compile(r'(?:^|\s|\[|\(|\-|#)\s*(\d+)\s*(?:$|\s|\]|\)|\-|\.)'),
        # 模式6: 作为最后的备用，匹配开头的数字
        re.compile(r'^(\d+)'),
    ]
    for pattern in patterns:
        match = pattern.search(basename)
        if match:
            try:
                # 优先使用最后一个非空捕获组，以支持更复杂的正则表达式
                num_str = [g for g in match.groups() if g is not None][-1]
                start_num = chinese_to_arabic(num_str)
                # 只要匹配成功，就认为这是一个有效的章节号
                if start_num is not None:
                    return (start_num, start_num)
            except (ValueError, IndexError):
                continue
    # 如果所有模式都失败，返回一个巨大的数字，确保它排在最后
    return (99999, 99999)

def natural_sort_key(filename):
    """
    为文件名生成自然排序键，支持阿拉伯数字、中文数字和英文数字。
    例如：'item 2' < 'item 10', '第二十章' > '第十章'
    """
    basename = os.path.basename(filename)
    
    # 构建一个正则表达式，用于分割字符串。
    # 这个表达式能识别连续的阿拉伯数字、中文数字字符，或者一个完整的英文数字单词。
    chinese_num_chars = ''.join(_CH_NUM_MAP.keys()) + ''.join(_CH_UNIT_MAP.keys()) + ''.join(_CH_SECTION_UNIT_MAP.keys())
    english_num_words = '|'.join(_EN_NUM_MAP.keys())
    
    # 使用 re.IGNORECASE 以匹配大小写不敏感的英文单词，并使用 raw f-string 避免警告
    pattern = fr'(\d+|[{re.escape(chinese_num_chars)}]+|{english_num_words})'
    parts = re.split(pattern, basename, flags=re.IGNORECASE)
    
    key = []
    for part in parts:
        if not part:
            continue
        
        part_lower = part.lower()
        
        # 1. 检查是否为阿拉伯数字
        if part_lower.isdigit():
            key.append(int(part_lower))
            continue
            
        # 2. 检查是否为英文数字
        if part_lower in _EN_NUM_MAP:
            key.append(_EN_NUM_MAP[part_lower])
            continue

        # 3. 检查是否为中文数字
        # 我们只尝试转换完全由中文数字字符组成的字符串部分
        if all(c in chinese_num_chars for c in part):
            try:
                num = chinese_to_arabic(part)
                key.append(num)
                continue
            except (ValueError, KeyError):
                # 如果转换失败，则作为普通文本处理
                pass
        
        # 4. 如果都不是，则作为普通文本
        key.append(part_lower)
            
    return key

def get_big_summary_sort_key(filename):
    """
    为"大总结"文件名生成排序键。
    它只关心文件名开头的章节号，并忽略所有后续的随机字符。
    """
    # get_chapter_range_from_filename 已被证明是健壮的，能从复杂字符串中提取第一个章节号
    start_num, _ = get_chapter_range_from_filename(filename)
    return start_num

def get_super_ultimate_summary_sort_key(filename):
    """
    为"超级总结"和"终极总结"文件名生成排序键。
    优先提取api编号，其次提取批次编号，保证排序的绝对健壮性。
    """
    basename = os.path.basename(filename)
    
    # 优先匹配 _api<数字>
    api_match = re.search(r'_api(\d+)', basename)
    if api_match:
        return (0, int(api_match.group(1))) # 返回元组(0, api_num)以确保api排序优先

    # 其次匹配 _auto_batch_<数字>
    batch_match = re.search(r'_auto_batch_(\d+)', basename)
    if batch_match:
        return (1, int(batch_match.group(1))) # 返回元组(1, batch_num)

    # 如果都匹配不到，返回一个大的元组，排在最后
    return (float('inf'), float('inf'))

def extract_numbers_from_filename(filename):
    """
    从文件名中提取所有数字并将其作为一个整数返回，用于排序。
    例如 'vol1_chap12.txt' -> 112
    """
    basename = os.path.basename(filename)
    digits = ''.join(re.findall(r'\d+', basename))
    if digits:
        return int(digits)
    return float('inf') # 如果没有数字，则排在最后

# --- Prompt Loading ---

def get_summarizer_cache_dir(novel_folder_path):
    """
    获取并确保存在用于存放所有总结缓存的根目录。
    """
    cache_dir = os.path.join(novel_folder_path, ".summarizer_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def load_all_prompts_for_run():
    """
    从缓存目录加载所有提示词，如果文件不存在则使用默认值。
    返回一个包含所有提示词文本的字典。
    """
    cache_dir = get_global_prompt_cache_dir()
    loaded_prompts = {}
    
    def _load(config):
        filename = config['filename']
        default_text = config['default']
        filepath = os.path.join(cache_dir, filename)
        
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            print(f"无法从文件 {filepath} 加载提示词, 将使用默认值。错误: {e}")
        return default_text

    for key, config in DEFAULT_PROMPTS.items():
        loaded_prompts[key] = {'text': _load(config), **config}
        
    return loaded_prompts

# --- Work Distribution ---

def _distribute_chapters_sequentially(chapters, apis):
    """按顺序将连续的章节块分配给API。"""
    if not apis:
        return {}
    if not chapters:
        return {api['id']: [] for api in apis}

    api_ids = [api['id'] for api in apis]
    distribution = {api_id: [] for api_id in api_ids}
    
    num_chapters = len(chapters)
    num_apis = len(api_ids)
    
    base_chunk_size = num_chapters // num_apis
    remainder = num_chapters % num_apis
    
    start_index = 0
    for i in range(num_apis):
        chunk_size = base_chunk_size + (1 if i < remainder else 0)
        end_index = start_index + chunk_size
        
        api_id = api_ids[i]
        distribution[api_id] = chapters[start_index:end_index]
        
        start_index = end_index
        
    return distribution

def _distribute_batches_sequentially(batches, apis):
    """按顺序将连续的批次块分配给API。"""
    if not apis:
        return {}
    if not batches:
        return {api['id']: [] for api in apis}
        
    api_ids = [api['id'] for api in apis]
    distribution = {api_id: [] for api_id in api_ids}

    num_batches = len(batches)
    num_apis = len(api_ids)

    base_chunk_size = num_batches // num_apis
    remainder = num_batches % num_apis

    start_index = 0
    for i in range(num_apis):
        chunk_size = base_chunk_size + (1 if i < remainder else 0)
        end_index = start_index + chunk_size
        
        api_id = api_ids[i]
        distribution[api_id] = batches[start_index:end_index]
        
        start_index = end_index
        
    return distribution

# --- Chapter Splitting Shared Logic ---

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
        first_num_str = (first_match.group(2) or first_match.group(3) or "").strip()
        last_num_str = (last_match.group(2) or last_match.group(3) or "").strip()

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

                filename = f"第{global_first_num}章-第{global_last_num}章.txt"
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
    content, output_directory_path, chapters_per_file, 
    handle_volumes, log_callback, chapter_pattern
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

        if chapters_in_buffer >= chapters_per_file:
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

async def read_files_and_join(files: List[str]) -> str:
    """异步读取多个文件的内容并将它们用分隔符连接起来。"""
    async def _read_file(f):
        if os.path.exists(f):
            try:
                async with aiofiles.open(f, 'r', encoding='utf-8') as handle:
                    return await handle.read()
            except Exception as e:
                print(f"Warning: Could not read file {f}: {e}")
                return ""
        print(f"Warning: File not found and skipped: {f}")
        return ""
    
    tasks = [_read_file(f) for f in files]
    contents = await asyncio.gather(*tasks)
    return "\n\n---\n\n".join(c for c in contents if c) 
