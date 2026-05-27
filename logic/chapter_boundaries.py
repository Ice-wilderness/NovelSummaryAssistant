import re
from dataclasses import dataclass
from typing import Iterable


DEFAULT_CHAPTER_PATTERN = re.compile(
    r'^\s*((第\s*[一二三四五六七八九十百千万亿零\d]+\s*(?:章|节|回)).*)',
    re.MULTILINE,
)

MAX_RAW_REGEX_LENGTH = 500
REGEX_PREFLIGHT_SAMPLE_CHARS = 20000
REGEX_PREFLIGHT_MAX_MATCHES = 2000


class ChapterSplitError(ValueError):
    """Structured chapter split failure that can be shown to users."""

    def __init__(self, code: str, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint


@dataclass(frozen=True)
class ChapterBoundary:
    index: int
    title: str
    start: int
    end: int
    line_number: int
    word_count: int
    matched: bool = True

    def to_preview_item(self) -> dict:
        item = {
            "index": self.index,
            "title": self.title,
            "line_number": self.line_number,
            "word_count": self.word_count,
        }
        if not self.matched:
            item["matched"] = False
        return item


def count_line_number(content: str, pos: int) -> int:
    return content[:pos].count('\n') + 1


def count_chinese_chars(text: str) -> int:
    return len(re.sub(r'\s', '', text))


def build_regex_from_simple_pattern(custom_pattern: str) -> str:
    if not custom_pattern or 'n' not in custom_pattern.lower():
        raise ChapterSplitError(
            "invalid_simple_pattern",
            "自定义规律不能为空，且必须包含 'n' 或 'N' 来代表章节号。",
            "请使用类似“第n章”的模式。",
        )

    parts = re.split('(n)', custom_pattern, flags=re.IGNORECASE)
    prefix = re.escape(parts[0])
    suffix = re.escape(parts[2]) if len(parts) > 2 else ''

    number_regex_part = r'([一二三四五六七八九十百千万亿零\d]+)'
    user_chapter_regex = fr"{prefix}\s*{number_regex_part}\s*{suffix}"
    final_pattern_str = fr"({user_chapter_regex}\s*.*)"
    return fr'^\s*{final_pattern_str}'


def compile_simple_pattern(custom_pattern: str) -> re.Pattern:
    return re.compile(build_regex_from_simple_pattern(custom_pattern), re.MULTILINE | re.IGNORECASE)


def _looks_like_nested_repeat(raw_pattern: str) -> bool:
    group_with_inner_repeat = re.compile(
        r"\((?:\?:|\?P<[^>]+>|\?[:=!<][^)]*)?[^()]{0,200}(?:\*|\+|\{\d+(?:,\d*)?\})[^()]{0,200}\)"
        r"\s*(?:\*|\+|\{\d+(?:,\d*)?\})"
    )
    return bool(group_with_inner_repeat.search(raw_pattern))


def validate_raw_pattern(raw_pattern: str) -> str:
    pattern = str(raw_pattern or "").strip()
    if not pattern:
        raise ChapterSplitError("empty_regex", "正则表达式不能为空。")
    if len(pattern) > MAX_RAW_REGEX_LENGTH:
        raise ChapterSplitError(
            "regex_too_long",
            f"正则表达式过长，最多允许 {MAX_RAW_REGEX_LENGTH} 个字符。",
            "请简化表达式，或拆成更明确的章节标题规则。",
        )
    if _looks_like_nested_repeat(pattern):
        raise ChapterSplitError(
            "high_risk_regex",
            "正则表达式包含高风险的嵌套重复结构，已阻止执行。",
            "请避免类似 (a+)+ 或 (.*)+ 的写法，改用更具体的章节标题模式。",
        )
    try:
        re.compile(pattern)
    except re.error as exc:
        raise ChapterSplitError(
            "invalid_regex",
            f"正则表达式语法无效: {exc}",
            "请检查括号、转义字符和重复量词。",
        ) from exc
    return pattern


def preflight_pattern(pattern: re.Pattern, sample_text: str) -> None:
    if not sample_text:
        return
    sample = sample_text[:REGEX_PREFLIGHT_SAMPLE_CHARS]
    match_count = 0
    for match in pattern.finditer(sample):
        match_count += 1
        if match.start() == match.end():
            raise ChapterSplitError(
                "regex_zero_width",
                "正则表达式会匹配空文本，无法作为章节标题规则。",
                "请确保表达式至少匹配实际章节标题文字。",
            )
        if match_count > REGEX_PREFLIGHT_MAX_MATCHES:
            raise ChapterSplitError(
                "regex_too_many_matches",
                "正则表达式在预检样本中匹配过多，已阻止执行。",
                "请收窄表达式，使其只匹配章节标题行。",
            )


def compile_raw_pattern(raw_pattern: str, sample_text: str = "") -> re.Pattern:
    pattern = validate_raw_pattern(raw_pattern)
    compiled = re.compile(pattern)
    if compiled.groups == 0:
        pattern = rf"^\s*(({pattern}).*)"
    final = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
    preflight_pattern(final, sample_text)
    return final


def compile_pattern_config(pattern_config, sample_text: str = "") -> re.Pattern:
    regex_mode = getattr(pattern_config, "regex_mode", "raw")
    pattern = getattr(pattern_config, "pattern", "")
    if regex_mode == "simple":
        compiled = compile_simple_pattern(pattern)
        preflight_pattern(compiled, sample_text)
        return compiled
    return compile_raw_pattern(pattern, sample_text=sample_text)


def boundaries_from_pattern(
    content: str,
    pattern: re.Pattern,
    *,
    no_match_message: str = "未能找到任何章节标题，请检查分割模式。",
) -> list[ChapterBoundary]:
    if not content.strip():
        raise ChapterSplitError("empty_content", "源文件内容不能为空。")

    matches = list(pattern.finditer(content))
    if not matches:
        raise ChapterSplitError("no_chapters", no_match_message)

    boundaries: list[ChapterBoundary] = []
    for i, match in enumerate(matches):
        if match.start() == match.end():
            raise ChapterSplitError(
                "zero_width_match",
                "章节标题规则匹配到了空文本，无法安全分割。",
            )
        title = match.group(1).strip() if match.lastindex and match.lastindex >= 1 else match.group(0).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        chapter_text = content[start:end]
        boundaries.append(
            ChapterBoundary(
                index=i + 1,
                title=title,
                start=start,
                end=end,
                line_number=count_line_number(content, start),
                word_count=count_chinese_chars(chapter_text),
            )
        )
    return boundaries


def default_boundaries(content: str) -> list[ChapterBoundary]:
    return boundaries_from_pattern(
        content,
        DEFAULT_CHAPTER_PATTERN,
        no_match_message="未匹配到默认章节标题，请检查源文件是否包含“第X章/节/回”格式。",
    )


def regex_boundaries(
    content: str,
    *,
    custom_pattern: str = "",
    pattern_config=None,
) -> tuple[list[ChapterBoundary], re.Pattern]:
    if pattern_config is not None:
        pattern = compile_pattern_config(pattern_config, sample_text=content)
    elif custom_pattern:
        pattern = compile_simple_pattern(custom_pattern)
        preflight_pattern(pattern, content)
    else:
        raise ChapterSplitError(
            "missing_regex",
            "正则模式需要提供 custom_pattern 或 pattern_config。",
        )
    return (
        boundaries_from_pattern(
            content,
            pattern,
            no_match_message="正则未匹配到任何章节标题，请检查表达式或切换配置。",
        ),
        pattern,
    )


def title_list_boundaries(content: str, titles: Iterable[str]) -> list[ChapterBoundary]:
    cleaned_titles = [str(title).strip() for title in titles if str(title).strip()]
    if not cleaned_titles:
        raise ChapterSplitError("empty_title_list", "标题列表模式需要提供 title_list。")

    escaped_titles = [re.escape(title) for title in cleaned_titles]
    pattern = re.compile(f'^\\s*({"|".join(escaped_titles)})\\s*$', re.MULTILINE)
    matches = list(pattern.finditer(content))
    matched_by_title = {match.group(1).strip(): match for match in matches}

    results: list[ChapterBoundary] = []
    for index, title in enumerate(cleaned_titles, start=1):
        match = matched_by_title.get(title)
        if not match:
            results.append(
                ChapterBoundary(
                    index=index,
                    title=title,
                    start=0,
                    end=0,
                    line_number=0,
                    word_count=0,
                    matched=False,
                )
            )
            continue
        match_index = matches.index(match)
        start = match.start()
        end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(content)
        chapter_text = content[start:end]
        results.append(
            ChapterBoundary(
                index=index,
                title=title,
                start=start,
                end=end,
                line_number=count_line_number(content, start),
                word_count=count_chinese_chars(chapter_text),
            )
        )

    if not any(boundary.matched for boundary in results):
        raise ChapterSplitError(
            "no_title_matches",
            "标题列表未匹配到任何章节，请检查标题是否与原文完全一致。",
        )
    return results


def matched_boundaries(boundaries: Iterable[ChapterBoundary]) -> list[ChapterBoundary]:
    return [boundary for boundary in boundaries if boundary.matched]
