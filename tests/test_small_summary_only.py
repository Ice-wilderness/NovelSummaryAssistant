import asyncio
import unittest
from unittest import mock

from logic.orchestrator import _build_novel_summary_stage_defs, run_summarization_process
from logic.utils import build_small_summary_batches


class _FakeStateManager:
    chapters = ["001.txt", "002.txt"]

    def __init__(self, completed_small=None):
        self.completed_small = set(completed_small or [])

    def get_initialization_log(self):
        return ""

    def get_pending_small_summary_chapters(self, chapter_paths, batch_size=1):
        pending = []
        for task_name, batch_paths in build_small_summary_batches(chapter_paths, batch_size):
            if not self.is_task_complete(task_name, "small_summary"):
                pending.extend(batch_paths)
        return pending

    def get_pending_tasks(self, *args, **kwargs):
        return []

    def is_task_complete(self, task_name, stage_name, sub_stage_name=None):
        return stage_name == "small_summary" and task_name in self.completed_small


class SmallSummaryOnlyOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    def test_stage_totals_count_small_summary_batches_not_chapters(self):
        fake_state_manager = _FakeStateManager()

        stage_defs = _build_novel_summary_stage_defs(
            use_fine_grained_flow=False,
            stop_after_small_summary=False,
            active_api_configs=[{"id": "api1"}],
            chapter_distribution={"api1": ["001.txt", "002.txt", "003.txt"]},
            state_manager=fake_state_manager,
            big_summary_batch_size=5,
            summary_batch_size=2,
        )

        small_stage = next(stage for stage in stage_defs if stage["id"] == "small_summary")
        self.assertEqual(small_stage["total"], 2)
        self.assertEqual(small_stage["completed"], 0)

    def test_stage_totals_include_existing_small_summary_batches(self):
        fake_state_manager = _FakeStateManager(completed_small={"small_batch_001_to_002.txt"})

        stage_defs = _build_novel_summary_stage_defs(
            use_fine_grained_flow=False,
            stop_after_small_summary=False,
            active_api_configs=[{"id": "api1"}],
            chapter_distribution={"api1": ["001.txt", "002.txt", "003.txt"]},
            state_manager=fake_state_manager,
            big_summary_batch_size=5,
            summary_batch_size=2,
        )

        small_stage = next(stage for stage in stage_defs if stage["id"] == "small_summary")
        self.assertEqual(small_stage["total"], 2)
        self.assertEqual(small_stage["completed"], 1)

    async def test_stop_after_small_summary_skips_later_stages(self):
        fake_state_manager = _FakeStateManager()
        api_configs = [{"id": "api1", "api_key_name": "API 1"}]

        with (
            mock.patch("logic.orchestrator.StateManager", return_value=fake_state_manager),
            mock.patch("logic.orchestrator.load_all_prompts_for_run", return_value={"prompt_small_summary": {"text": "summary"}}),
            mock.patch("logic.orchestrator.run_small_summary_stage", new=mock.AsyncMock()) as small_summary,
            mock.patch("logic.orchestrator.run_big_summary_stage", new=mock.AsyncMock()) as big_summary,
            mock.patch("logic.orchestrator.run_super_summary_for_api", new=mock.AsyncMock()) as super_summary,
            mock.patch("logic.orchestrator.run_automated_super_summary_stage", new=mock.AsyncMock()) as automated_super_summary,
            mock.patch("logic.orchestrator.run_ultimate_summary_stage", new=mock.AsyncMock()) as ultimate_summary,
        ):
            success = await run_summarization_process(
                novel_folder_path="novel",
                active_api_configs=api_configs,
                log_callback=None,
                pause_event=asyncio.Event(),
                summary_batch_size=2,
                big_summary_batch_size=5,
                super_summary_threshold=5,
                ultimate_api_id="api1",
                word_counts={},
                use_fine_grained_flow=False,
                stop_after_small_summary=True,
            )

        self.assertTrue(success)
        small_summary.assert_awaited_once()
        self.assertEqual(small_summary.await_args.args[-1], 2)
        big_summary.assert_not_awaited()
        super_summary.assert_not_awaited()
        automated_super_summary.assert_not_awaited()
        ultimate_summary.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
