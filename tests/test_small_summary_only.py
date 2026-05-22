import asyncio
import unittest
from unittest import mock

from logic.orchestrator import run_summarization_process


class _FakeStateManager:
    chapters = ["001.txt", "002.txt"]

    def get_initialization_log(self):
        return ""

    def get_pending_small_summary_chapters(self, chapter_paths, batch_size=1):
        return list(chapter_paths)


class SmallSummaryOnlyOrchestratorTests(unittest.IsolatedAsyncioTestCase):
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
