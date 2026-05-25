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
    USER_FACING_SUPER_CHAR_P2_SUBDIR,
    USER_FACING_SUPER_PLOT_P1_SUBDIR,
    USER_FACING_SUPER_PLOT_P2_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P1_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P2_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P1_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P2_SUBDIR,
)
from logic.automated_super_summary import run_automated_super_summary_stage
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

    def test_completed_ultimate_summary_requires_output_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "001.txt").write_text("chapter", encoding="utf-8")
            cache_dir = root / ".summarizer_cache"
            cache_dir.mkdir()
            (cache_dir / "task_id.txt").write_text("task", encoding="utf-8")
            ultimate_tasks = [
                ("ultimate_summary_plot_p1", USER_FACING_ULTIMATE_PLOT_P1_SUBDIR),
                ("ultimate_summary_plot_p2", USER_FACING_ULTIMATE_PLOT_P2_SUBDIR),
                ("ultimate_summary_char_p1", USER_FACING_ULTIMATE_CHAR_P1_SUBDIR),
                ("ultimate_summary_char_p2", USER_FACING_ULTIMATE_CHAR_P2_SUBDIR),
            ]
            (cache_dir / "state_task.json").write_text(
                json.dumps(
                    {
                        "ultimate_summary": {
                            task_name: True for task_name, _ in ultimate_tasks
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            manager = StateManager(str(root))

            self.assertFalse(manager.is_ultimate_summary_stage_complete())
            self.assertFalse(
                manager.is_task_complete("ultimate_summary_plot_p1", "ultimate_summary")
            )

            for task_name, subdir in ultimate_tasks:
                output_dir = cache_dir / subdir
                output_dir.mkdir(parents=True)
                (output_dir / f"{task_name}_by_api.md").write_text("ultimate", encoding="utf-8")

            self.assertTrue(manager.is_ultimate_summary_stage_complete())


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


class AutomatedSuperSummaryResumeTests(unittest.IsolatedAsyncioTestCase):
    async def test_automated_super_summary_marks_batch_without_api_suffix_and_skips_after_restart(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "001.txt").write_text("chapter", encoding="utf-8")
            cache_dir = root / ".summarizer_cache"
            cache_dir.mkdir()
            (cache_dir / "task_id.txt").write_text("task", encoding="utf-8")
            for subdir in [USER_FACING_BIG_PLOT_SUBDIR, USER_FACING_BIG_CHAR_SUBDIR]:
                (cache_dir / subdir).mkdir(parents=True)
            for index in range(1, 5):
                (cache_dir / USER_FACING_BIG_PLOT_SUBDIR / f"big_batch_{index}_api.md").write_text("plot", encoding="utf-8")
                (cache_dir / USER_FACING_BIG_CHAR_SUBDIR / f"big_batch_{index}_api.md").write_text("char", encoding="utf-8")

            manager = StateManager(str(root))
            first_llm = mock.AsyncMock(return_value="summary")
            with mock.patch(
                "logic.automated_super_summary.get_llm_summary_with_config",
                new=first_llm,
            ):
                await run_automated_super_summary_stage(
                    [{"id": "api1", "api_key_name": "API 1"}],
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
                    super_summary_threshold=2,
                )

            self.assertEqual(first_llm.await_count, 8)
            state = json.loads((cache_dir / "state_task.json").read_text(encoding="utf-8"))
            self.assertIn("auto_batch_1", state["super_summary_plot"])
            self.assertNotIn("auto_batch_1_api1", state["super_summary_plot"])

            restarted_manager = StateManager(str(root))
            second_llm = mock.AsyncMock(return_value="summary")
            with mock.patch(
                "logic.automated_super_summary.get_llm_summary_with_config",
                new=second_llm,
            ):
                await run_automated_super_summary_stage(
                    [{"id": "api1", "api_key_name": "API 1"}],
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
                    restarted_manager,
                    super_summary_threshold=2,
                )

            second_llm.assert_not_awaited()

    async def test_automated_super_summary_skips_existing_outputs_with_legacy_state_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "001.txt").write_text("chapter", encoding="utf-8")
            cache_dir = root / ".summarizer_cache"
            cache_dir.mkdir()
            (cache_dir / "task_id.txt").write_text("task", encoding="utf-8")
            (cache_dir / "state_task.json").write_text(
                json.dumps({"super_summary_plot": {"auto_batch_1_api1": True}}, ensure_ascii=False),
                encoding="utf-8",
            )
            (cache_dir / USER_FACING_BIG_PLOT_SUBDIR).mkdir(parents=True)
            for index in range(1, 3):
                (cache_dir / USER_FACING_BIG_PLOT_SUBDIR / f"big_batch_{index}_api.md").write_text("plot", encoding="utf-8")
            for subdir, filename in [
                (USER_FACING_SUPER_PLOT_P1_SUBDIR, "super_summary_auto_batch_1_plot_p1.md"),
                (USER_FACING_SUPER_PLOT_P2_SUBDIR, "super_summary_auto_batch_1_plot_p2.md"),
            ]:
                (cache_dir / subdir).mkdir(parents=True)
                (cache_dir / subdir / filename).write_text("super", encoding="utf-8")

            manager = StateManager(str(root))
            llm = mock.AsyncMock(return_value="summary")
            with mock.patch(
                "logic.automated_super_summary.get_llm_summary_with_config",
                new=llm,
            ):
                await run_automated_super_summary_stage(
                    [{"id": "api1", "api_key_name": "API 1"}],
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
                    super_summary_threshold=2,
                )

            llm.assert_not_awaited()

    async def test_automated_super_summary_preserves_pending_batch_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "001.txt").write_text("chapter", encoding="utf-8")
            cache_dir = root / ".summarizer_cache"
            cache_dir.mkdir()
            (cache_dir / "task_id.txt").write_text("task", encoding="utf-8")
            (cache_dir / USER_FACING_BIG_PLOT_SUBDIR).mkdir(parents=True)
            for index in range(1, 5):
                (cache_dir / USER_FACING_BIG_PLOT_SUBDIR / f"big_batch_{index}_api.md").write_text("plot", encoding="utf-8")
            for subdir, filename in [
                (USER_FACING_SUPER_PLOT_P1_SUBDIR, "super_summary_auto_batch_1_plot_p1.md"),
                (USER_FACING_SUPER_PLOT_P2_SUBDIR, "super_summary_auto_batch_1_plot_p2.md"),
            ]:
                (cache_dir / subdir).mkdir(parents=True)
                (cache_dir / subdir / filename).write_text("super", encoding="utf-8")

            manager = StateManager(str(root))
            llm = mock.AsyncMock(return_value="summary")
            with mock.patch(
                "logic.automated_super_summary.get_llm_summary_with_config",
                new=llm,
            ):
                await run_automated_super_summary_stage(
                    [{"id": "api1", "api_key_name": "API 1"}],
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
                    super_summary_threshold=2,
                )

            self.assertEqual(
                [call.kwargs["task_info"]["batch_name"] for call in llm.await_args_list],
                ["auto_batch_2", "auto_batch_2"],
            )


if __name__ == "__main__":
    unittest.main()
