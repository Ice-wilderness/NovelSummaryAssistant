import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from logic.prompts import (
    USER_FACING_BIG_CHAR_SUBDIR,
    USER_FACING_BIG_PLOT_SUBDIR,
    USER_FACING_SMALL_CHAR_SUBDIR,
    USER_FACING_SMALL_PLOT_SUBDIR,
    USER_FACING_SUPER_CHAR_P1_SUBDIR,
    USER_FACING_SUPER_PLOT_P1_SUBDIR,
)
from logic.state_manager import StateManager
from logic.summarization_stages import run_super_summary_for_api


class StateManagerResumeTests(unittest.TestCase):
    def test_pending_small_summary_uses_batch_task_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for name in ["001.txt", "002.txt", "003.txt"]:
                (root / name).write_text(name, encoding="utf-8")
            cache_dir = root / ".summarizer_cache"
            cache_dir.mkdir()
            (cache_dir / "task_id.txt").write_text("task", encoding="utf-8")
            task_name = "small_batch_001_to_002.txt"
            (cache_dir / "state_task.json").write_text(
                json.dumps({"small_summary": {task_name: True}}, ensure_ascii=False),
                encoding="utf-8",
            )
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR).mkdir(parents=True)
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR).mkdir(parents=True)
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR / "small_batch_001_to_002.md").write_text("plot", encoding="utf-8")
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR / task_name).write_text("char", encoding="utf-8")

            manager = StateManager(str(root))

            self.assertEqual(
                [Path(path).name for path in manager.get_pending_tasks("small_summary", batch_size=2)],
                ["003.txt"],
            )

    def test_completed_big_summary_requires_output_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "001.txt").write_text("chapter", encoding="utf-8")
            cache_dir = root / ".summarizer_cache"
            cache_dir.mkdir()
            (cache_dir / "task_id.txt").write_text("task", encoding="utf-8")
            (cache_dir / "state_task.json").write_text(
                """
{
    "small_summary": {"001.txt": true},
    "small_summary_assignment": {"001.txt": "api-current"},
    "big_summary": {"big_batch_001_to_001_plot": true}
}
""".strip(),
                encoding="utf-8",
            )
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR).mkdir(parents=True)
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR).mkdir(parents=True)
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR / "001.txt").write_text("plot", encoding="utf-8")
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR / "001.txt").write_text("char", encoding="utf-8")

            manager = StateManager(str(root))

            self.assertFalse(
                manager.is_task_complete("big_batch_001_to_001", "big_summary", "plot")
            )

            output_dir = cache_dir / USER_FACING_BIG_PLOT_SUBDIR
            output_dir.mkdir(parents=True)
            (output_dir / "big_batch_001_to_001_api1.md").write_text("big", encoding="utf-8")

            self.assertTrue(
                manager.is_task_complete("big_batch_001_to_001", "big_summary", "plot")
            )
            self.assertEqual(
                manager.get_completed_big_summary_batches_for_api("api-current", "plot", 5),
                ["big_batch_001_to_001"],
            )


class SuperSummaryResumeTests(unittest.IsolatedAsyncioTestCase):
    async def test_super_summary_uses_imported_big_summary_with_legacy_api_suffix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "001.txt").write_text("chapter", encoding="utf-8")
            cache_dir = root / ".summarizer_cache"
            cache_dir.mkdir()
            (cache_dir / "task_id.txt").write_text("task", encoding="utf-8")
            (cache_dir / "state_task.json").write_text(
                """
{
    "small_summary": {"001.txt": true},
    "small_summary_assignment": {"001.txt": "api-current"},
    "big_summary": {
        "big_batch_001_to_001_plot": true,
        "big_batch_001_to_001_char": true
    }
}
""".strip(),
                encoding="utf-8",
            )
            for subdir in [
                USER_FACING_SMALL_PLOT_SUBDIR,
                USER_FACING_SMALL_CHAR_SUBDIR,
                USER_FACING_BIG_PLOT_SUBDIR,
                USER_FACING_BIG_CHAR_SUBDIR,
            ]:
                (cache_dir / subdir).mkdir(parents=True)
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR / "001.txt").write_text("plot", encoding="utf-8")
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR / "001.txt").write_text("char", encoding="utf-8")
            (cache_dir / USER_FACING_BIG_PLOT_SUBDIR / "big_batch_001_to_001_api1.txt").write_text("big plot", encoding="utf-8")
            (cache_dir / USER_FACING_BIG_CHAR_SUBDIR / "big_batch_001_to_001_api1.txt").write_text("big char", encoding="utf-8")
            manager = StateManager(str(root))

            with mock.patch(
                "logic.summarization_stages.get_llm_summary_with_config",
                new=mock.AsyncMock(return_value="summary"),
            ):
                await run_super_summary_for_api(
                    {"id": "api-current", "api_key_name": "Current API"},
                    str(root),
                    {
                        "prompt_super_plot_p1": {},
                        "prompt_super_plot_p2": {},
                        "prompt_super_char_p1": {},
                        "prompt_super_char_p2": {},
                    },
                    {},
                    None,
                    None,
                    manager,
                    big_summary_batch_size=5,
                )

            self.assertTrue(
                (
                    cache_dir
                    / USER_FACING_SUPER_PLOT_P1_SUBDIR
                    / "super_summary_Current_API_plot_p1.md"
                ).exists()
            )
            self.assertTrue(
                (
                    cache_dir
                    / USER_FACING_SUPER_CHAR_P1_SUBDIR
                    / "super_summary_Current_API_char_p1.md"
                ).exists()
            )


if __name__ == "__main__":
    unittest.main()
