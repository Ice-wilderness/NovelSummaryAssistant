import re


def extract_tag_content(text, tag_name, end_tag_name=None, stop_before_tags=None):
    """
    从文本中提取被 <tag_name>...</tag_name> 包裹的内容。
    容错：忽略标签大小写、标签名周围多余空格、闭合标签缺失时回退到文末。
    返回标签内部内容，未匹配则返回空字符串。
    """
    escaped_start = re.escape(tag_name)
    escaped_end = re.escape(end_tag_name or tag_name)
    pattern = re.compile(
        rf"<\s*{escaped_start}\s*>(.*?)<\s*/\s*{escaped_end}\s*>",
        re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(text)
    if match:
        return match.group(1).strip()

    start_pattern = re.compile(
        rf"<\s*{escaped_start}\s*>",
        re.DOTALL | re.IGNORECASE
    )
    start_match = start_pattern.search(text)
    if start_match:
        content_start = start_match.end()
        content_end = len(text)
        for stop_tag in stop_before_tags or []:
            stop_pattern = re.compile(
                rf"<\s*{re.escape(stop_tag)}\s*>",
                re.DOTALL | re.IGNORECASE
            )
            stop_match = stop_pattern.search(text, content_start)
            if stop_match:
                content_end = min(content_end, stop_match.start())
        return text[content_start:content_end].strip()

    return ""


def extract_summary_content(text):
    """从 <summary_content> 标签中提取剧情总结内容。"""
    return extract_tag_content(text, "summary_content", stop_before_tags=["character_content", "character_info_block_start"])


def extract_character_content(text):
    """从 <character_content> 标签中提取角色总结内容。"""
    return extract_tag_content(text, "character_content", stop_before_tags=["summary_content"])


def extract_character_info_from_summary(summary_text):
    """
    [已废弃] 从旧版 <character_info_block_start/end> 或新版 <character_content> 标签中提取角色信息块。
    保留此函数以维持向后兼容。
    """
    result = extract_character_content(summary_text)
    if result:
        return result
    return extract_tag_content(summary_text, "character_info_block_start", end_tag_name="character_info_block_end")
