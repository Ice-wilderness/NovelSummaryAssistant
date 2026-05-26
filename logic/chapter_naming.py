import os
import re


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
    # 提取字符串中的阿拉伯数字（如 "第1章" → 1）
    digit_match = re.search(r'\d+', cn_str)
    if digit_match:
        return int(digit_match.group())
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
        return (0, int(api_match.group(1)))  # 返回元组(0, api_num)以确保api排序优先

    # 其次匹配 _auto_batch_<数字>
    batch_match = re.search(r'_auto_batch_(\d+)', basename)
    if batch_match:
        return (1, int(batch_match.group(1)))  # 返回元组(1, batch_num)

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
    return float('inf')  # 如果没有数字，则排在最后
