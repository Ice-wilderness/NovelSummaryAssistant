import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from logic.chapter_splitter import split_novel_into_chapter_files
from logic.prompts import USER_FACING_SMALL_CHAR_SUBDIR, USER_FACING_SMALL_PLOT_SUBDIR
from logic.state_manager import StateManager
from logic.summarization_stages import run_small_summary_stage
from logic.utils import build_small_summary_batches


class ChapterGranularityTests(unittest.TestCase):
    def test_splitter_writes_one_zero_padded_file_per_chapter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "novel.txt"
            output_dir = root / "out"
            source.write_text(
                "第一章 开始\n正文一\n第二章 继续\n正文二\n第三章 结束\n正文三",
                encoding="utf-8",
            )

            success, count = split_novel_into_chapter_files(
                str(source),
                str(output_dir),
                handle_volumes=False,
                log_callback=lambda *args, **kwargs: None,
                mode="default",
            )

            self.assertTrue(success)
            self.assertEqual(count, 3)
            self.assertEqual(
                sorted(path.name for path in output_dir.glob("*.txt")),
                ["第001章.txt", "第002章.txt", "第003章.txt"],
            )

    def test_small_summary_batch_names_keep_single_chapter_compatibility(self):
        self.assertEqual(
            build_small_summary_batches(["001.txt", "002.txt", "003.txt"], 2),
            [
                ("small_batch_001_to_002.txt", ["001.txt", "002.txt"]),
                ("003.txt", ["003.txt"]),
            ],
        )


class SmallSummaryBatchStageTests(unittest.IsolatedAsyncioTestCase):
    async def test_small_summary_stage_writes_one_output_per_summary_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            chapters = []
            for name, content in [
                ("001.txt", "one"),
                ("002.txt", "two"),
                ("003.txt", "three"),
            ]:
                path = root / name
                path.write_text(content, encoding="utf-8")
                chapters.append(str(path))
            manager = StateManager(str(root))
            prompts = {"prompt_small_summary": {"text": "summarize"}}
            api_config = {"id": "api1", "api_key_name": "API 1"}

            with mock.patch(
                "logic.summarization_stages.get_llm_summary_with_config",
                new=mock.AsyncMock(
                    return_value=(
                        "<summary_content>plot</summary_content>"
                        "<character_content>char</character_content>"
                    )
                ),
            ) as summary_call:
                await run_small_summary_stage(
                    chapters,
                    [api_config],
                    prompts,
                    str(root),
                    None,
                    asyncio.Event(),
                    manager,
                    {},
                    summary_batch_size=2,
                )

            cache_dir = root / ".summarizer_cache"
            self.assertTrue(
                (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR / "small_batch_001_to_002.txt").exists()
            )
            self.assertTrue((cache_dir / USER_FACING_SMALL_PLOT_SUBDIR / "003.txt").exists())
            self.assertTrue(
                manager.is_task_complete("small_batch_001_to_002.txt", "small_summary")
            )
            self.assertEqual(summary_call.await_count, 2)
            first_params = summary_call.await_args_list[0].args[2]
            self.assertIn("001.txt", first_params["current_chunk_text"])
            self.assertIn("002.txt", first_params["current_chunk_text"])


if __name__ == "__main__":
    unittest.main()
