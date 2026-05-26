import json
import os
import tempfile
import unittest
from unittest import mock

from logic import article_summary_logic


class ArticleSummaryLogicTests(unittest.IsolatedAsyncioTestCase):
    async def test_article_summary_process_writes_state_and_outputs(self):
        async def fake_summary(api_config, prompt_config, format_args, log_callback, **kwargs):
            filename = prompt_config.get("filename")
            if filename == "prompt_article_section.txt":
                return f"section:{format_args['filename_for_context']}"
            return "final-summary"

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, "1.txt")
            with open(source_path, "w", encoding="utf-8") as f:
                f.write("article body")
            skipped_path = os.path.join(tmpdir, "2.txt")
            with open(skipped_path, "w", encoding="utf-8") as f:
                f.write("skip body")

            logs = []
            api_configs = [{"id": "api1", "url": "http://example.test/v1", "key": "k", "model": "m"}]

            with mock.patch(
                "logic.article_summary_logic.get_llm_summary_with_config",
                side_effect=fake_summary,
            ):
                result = await article_summary_logic.run_article_summary_process(
                    source_folder_path=tmpdir,
                    active_api_configs=api_configs,
                    gui_log_callback=lambda *args, **kwargs: logs.append((args, kwargs)),
                    gui_pause_event=None,
                    gui_stop_event=None,
                    word_counts={"section": "100", "final": "200"},
                    selected_files=["1.txt"],
                    output_subfolder="article_output",
                )

            self.assertTrue(result)
            self.assertEqual(result.status, "success")
            cache_dir = os.path.join(tmpdir, "article_output", ".summarizer_cache")
            section_path = os.path.join(
                cache_dir,
                article_summary_logic.USER_FACING_ARTICLE_SECTION_SUBDIR,
                "summary_1.txt",
            )
            skipped_section_path = os.path.join(
                cache_dir,
                article_summary_logic.USER_FACING_ARTICLE_SECTION_SUBDIR,
                "summary_2.txt",
            )
            final_path = os.path.join(
                cache_dir,
                article_summary_logic.USER_FACING_ARTICLE_FINAL_SUBDIR,
                "最终总结_全文.txt",
            )
            state_path = os.path.join(cache_dir, article_summary_logic.ARTICLE_STATE_FILENAME)

            self.assertTrue(os.path.exists(section_path))
            self.assertFalse(os.path.exists(skipped_section_path))
            self.assertTrue(os.path.exists(final_path))
            self.assertTrue(os.path.exists(state_path))
            with open(final_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "final-summary")

    async def test_article_summary_process_returns_partial_when_section_fails(self):
        async def fake_summary(api_config, prompt_config, format_args, log_callback, **kwargs):
            filename = prompt_config.get("filename")
            if filename == "prompt_article_section.txt":
                if format_args["filename_for_context"] == "2.txt":
                    raise RuntimeError("section boom")
                return f"section:{format_args['filename_for_context']}"
            return "final-from-partial"

        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["1.txt", "2.txt"]:
                with open(os.path.join(tmpdir, name), "w", encoding="utf-8") as f:
                    f.write(f"article {name}")

            api_configs = [{"id": "api1", "url": "http://example.test/v1", "key": "k", "model": "m"}]

            with mock.patch(
                "logic.article_summary_logic.get_llm_summary_with_config",
                side_effect=fake_summary,
            ):
                result = await article_summary_logic.run_article_summary_process(
                    source_folder_path=tmpdir,
                    active_api_configs=api_configs,
                    gui_log_callback=lambda *args, **kwargs: None,
                    gui_pause_event=None,
                    gui_stop_event=None,
                    word_counts={"section": "100", "final": "200"},
                    output_subfolder="article_output",
                )

            cache_dir = os.path.join(tmpdir, "article_output", ".summarizer_cache")
            final_path = os.path.join(
                cache_dir,
                article_summary_logic.USER_FACING_ARTICLE_FINAL_SUBDIR,
                "最终总结_全文.txt",
            )
            state_path = os.path.join(cache_dir, article_summary_logic.ARTICLE_STATE_FILENAME)

            self.assertTrue(result)
            self.assertEqual(result.status, "partial_failed")
            self.assertTrue(os.path.exists(final_path))
            self.assertEqual(result.final_output_path, final_path)
            self.assertIn("2.txt", result.warnings[0])
            self.assertEqual(result.failed_sections[0]["filename"], "2.txt")
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.assertEqual(state["failed_sections"][0]["filename"], "2.txt")
            self.assertIn("结果可能不完整", state["partial_warnings"][0])

    async def test_article_summary_process_fails_when_all_sections_fail(self):
        async def fake_summary(api_config, prompt_config, format_args, log_callback, **kwargs):
            raise RuntimeError("section boom")

        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "1.txt"), "w", encoding="utf-8") as f:
                f.write("article body")
            api_configs = [{"id": "api1", "url": "http://example.test/v1", "key": "k", "model": "m"}]

            with mock.patch(
                "logic.article_summary_logic.get_llm_summary_with_config",
                side_effect=fake_summary,
            ):
                result = await article_summary_logic.run_article_summary_process(
                    source_folder_path=tmpdir,
                    active_api_configs=api_configs,
                    gui_log_callback=lambda *args, **kwargs: None,
                    gui_pause_event=None,
                    gui_stop_event=None,
                    word_counts={"section": "100", "final": "200"},
                    output_subfolder="article_output",
                )

            cache_dir = os.path.join(tmpdir, "article_output", ".summarizer_cache")
            final_path = os.path.join(
                cache_dir,
                article_summary_logic.USER_FACING_ARTICLE_FINAL_SUBDIR,
                "最终总结_全文.txt",
            )

            self.assertFalse(result)
            self.assertEqual(result.status, "failed")
            self.assertFalse(os.path.exists(final_path))

    async def test_article_summary_process_fails_when_final_generation_fails(self):
        async def fake_summary(api_config, prompt_config, format_args, log_callback, **kwargs):
            filename = prompt_config.get("filename")
            if filename == "prompt_article_section.txt":
                return "section-summary"
            raise RuntimeError("final boom")

        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "1.txt"), "w", encoding="utf-8") as f:
                f.write("article body")
            api_configs = [{"id": "api1", "url": "http://example.test/v1", "key": "k", "model": "m"}]

            with mock.patch(
                "logic.article_summary_logic.get_llm_summary_with_config",
                side_effect=fake_summary,
            ):
                result = await article_summary_logic.run_article_summary_process(
                    source_folder_path=tmpdir,
                    active_api_configs=api_configs,
                    gui_log_callback=lambda *args, **kwargs: None,
                    gui_pause_event=None,
                    gui_stop_event=None,
                    word_counts={"section": "100", "final": "200"},
                    output_subfolder="article_output",
                )

            self.assertFalse(result)
            self.assertEqual(result.status, "failed")
            self.assertIn("final boom", result.error)


if __name__ == "__main__":
    unittest.main()
