import os
import unittest
from unittest import mock

from logic import custom_summary_logic


class CustomSummaryLogicTests(unittest.IsolatedAsyncioTestCase):
    async def test_custom_summary_process_returns_success(self):
        async def fake_read(path):
            return f"content:{os.path.basename(path)}"

        logs = []
        with mock.patch(
            "logic.custom_summary_logic.utils.read_file_content_robustly_async",
            side_effect=fake_read,
        ), mock.patch(
            "logic.custom_summary_logic.call_llm_api",
            new=mock.AsyncMock(return_value=(("custom-output", 1.0, 13), None)),
        ):
            result = await custom_summary_logic.run_custom_summary_process(
                selected_file_paths=["a.txt", "b.txt"],
                user_prompt="summarize",
                api_config={"id": "api1"},
                pause_event=None,
                log_callback=logs.append,
            )

        self.assertTrue(result)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.output_text, "custom-output")
        self.assertEqual(result.warnings, [])

    async def test_custom_summary_process_returns_partial_when_material_read_fails(self):
        async def fake_read(path):
            if os.path.basename(path) == "bad.txt":
                raise OSError("cannot read")
            return "good content"

        with mock.patch(
            "logic.custom_summary_logic.utils.read_file_content_robustly_async",
            side_effect=fake_read,
        ), mock.patch(
            "logic.custom_summary_logic.call_llm_api",
            new=mock.AsyncMock(return_value=(("partial-output", 1.0, 14), None)),
        ):
            result = await custom_summary_logic.run_custom_summary_process(
                selected_file_paths=["good.txt", "bad.txt"],
                user_prompt="summarize",
                api_config={"id": "api1"},
                pause_event=None,
                log_callback=lambda *_args, **_kwargs: None,
            )

        self.assertTrue(result)
        self.assertEqual(result.status, "partial_failed")
        self.assertEqual(result.output_text, "partial-output")
        self.assertIn("bad.txt", result.warnings[0])
        self.assertEqual(result.failed_source_files[0]["filename"], "bad.txt")

    async def test_custom_summary_process_fails_when_all_materials_fail(self):
        with mock.patch(
            "logic.custom_summary_logic.utils.read_file_content_robustly_async",
            new=mock.AsyncMock(side_effect=OSError("cannot read")),
        ), mock.patch(
            "logic.custom_summary_logic.call_llm_api",
            new=mock.AsyncMock(),
        ) as call_api:
            result = await custom_summary_logic.run_custom_summary_process(
                selected_file_paths=["bad.txt"],
                user_prompt="summarize",
                api_config={"id": "api1"},
                pause_event=None,
                log_callback=lambda *_args, **_kwargs: None,
            )

        self.assertFalse(result)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.failed_source_files[0]["filename"], "bad.txt")
        call_api.assert_not_called()

    async def test_custom_summary_process_fails_when_api_call_fails(self):
        with mock.patch(
            "logic.custom_summary_logic.utils.read_file_content_robustly_async",
            new=mock.AsyncMock(return_value="good content"),
        ), mock.patch(
            "logic.custom_summary_logic.call_llm_api",
            new=mock.AsyncMock(return_value=(None, "api boom")),
        ):
            result = await custom_summary_logic.run_custom_summary_process(
                selected_file_paths=["good.txt"],
                user_prompt="summarize",
                api_config={"id": "api1"},
                pause_event=None,
                log_callback=lambda *_args, **_kwargs: None,
            )

        self.assertFalse(result)
        self.assertEqual(result.status, "failed")
        self.assertIn("API调用失败", result.error)


if __name__ == "__main__":
    unittest.main()
