import unittest

from logic.chapter_boundaries import (
    ChapterSplitError,
    boundaries_from_pattern,
    compile_raw_pattern,
    default_boundaries,
    regex_boundaries,
    title_list_boundaries,
)
from webui_backend.config_models import PatternConfig


class ChapterBoundaryTests(unittest.TestCase):
    def test_default_boundaries_include_line_and_word_counts(self):
        content = "序言\n第一章 开始\n正文一\n第二章 继续\n正文二"

        boundaries = default_boundaries(content)

        self.assertEqual([item.title for item in boundaries], ["第一章 开始", "第二章 继续"])
        self.assertEqual(boundaries[0].line_number, 2)
        self.assertGreater(boundaries[0].word_count, 0)

    def test_simple_regex_boundaries_use_shared_builder(self):
        content = "第1章 开始\n正文一\n第2章 继续\n正文二"

        boundaries, pattern = regex_boundaries(content, custom_pattern="第n章")

        self.assertEqual(len(boundaries), 2)
        self.assertIn("第", pattern.pattern)
        self.assertEqual(boundaries[1].title, "第2章 继续")

    def test_raw_regex_without_groups_is_wrapped_for_titles(self):
        content = "第1章 开始\n正文一\n第2章 继续\n正文二"
        pattern = compile_raw_pattern(r"第\s*\d+\s*章", sample_text=content)

        boundaries = boundaries_from_pattern(content, pattern)

        self.assertEqual([item.title for item in boundaries], ["第1章 开始", "第2章 继续"])

    def test_raw_regex_with_groups_is_used_directly(self):
        content = "第1章 开始\n正文一\n第2章 继续\n正文二"
        config = PatternConfig(
            id="raw",
            name="raw",
            regex_mode="raw",
            pattern=r"^\s*((第\s*(\d+)\s*章).*)",
        )

        boundaries, pattern = regex_boundaries(content, pattern_config=config)

        self.assertEqual(len(boundaries), 2)
        self.assertEqual(pattern.groups, 3)

    def test_title_list_boundaries_include_unmatched_items(self):
        content = "第一章 开始\n正文一\n第三章 结束\n正文三"

        boundaries = title_list_boundaries(content, ["第一章 开始", "第二章 缺失", "第三章 结束"])

        self.assertEqual(len(boundaries), 3)
        self.assertTrue(boundaries[0].matched)
        self.assertFalse(boundaries[1].matched)
        self.assertEqual(boundaries[1].line_number, 0)
        self.assertTrue(boundaries[2].matched)

    def test_no_matching_boundaries_raise_structured_error(self):
        with self.assertRaisesRegex(ChapterSplitError, "未匹配到默认章节标题"):
            default_boundaries("没有章节标题")

    def test_raw_regex_rejects_invalid_syntax(self):
        with self.assertRaisesRegex(ChapterSplitError, "语法无效"):
            compile_raw_pattern("(")

    def test_raw_regex_rejects_overlong_pattern(self):
        with self.assertRaisesRegex(ChapterSplitError, "过长"):
            compile_raw_pattern("a" * 501)

    def test_raw_regex_rejects_high_risk_nested_repeat(self):
        with self.assertRaisesRegex(ChapterSplitError, "高风险"):
            compile_raw_pattern(r"(a+)+$")

    def test_raw_regex_preflight_rejects_zero_width_matches(self):
        with self.assertRaisesRegex(ChapterSplitError, "空文本"):
            compile_raw_pattern(r"(?=(第))", sample_text="第一章 开始")


if __name__ == "__main__":
    unittest.main()
