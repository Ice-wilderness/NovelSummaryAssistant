import tempfile
import unittest
from unittest import mock

from logic.llm_api import PromptFormattingError
from logic.prompts import DEFAULT_PROMPTS
from logic.trigger_scan.prompts import (
    TRIGGER_COARSE_SCAN_PROMPT_KEY,
    TRIGGER_PRECISE_SCAN_PROMPT_KEY,
    TRIGGER_SCAN_PROMPT_KEYS,
    TRIGGER_VERIFICATION_PROMPT_KEY,
    load_trigger_scan_prompt_configs,
    render_trigger_prompt_messages,
    required_trigger_prompt_variables,
)
from webui_backend.config_service import (
    reset_workflow_prompt_node,
    update_workflow_prompt_node,
)


def _variables_for(prompt_key):
    return {
        name: f"value:{name}"
        for name in required_trigger_prompt_variables(prompt_key)
    }


class TriggerScanPromptTests(unittest.TestCase):
    def test_default_prompt_loading_and_rendering(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("logic.utils.get_global_prompt_cache_dir", return_value=tmpdir):
                prompts = load_trigger_scan_prompt_configs()

        self.assertEqual(set(prompts.keys()), set(TRIGGER_SCAN_PROMPT_KEYS))
        self.assertEqual(
            prompts[TRIGGER_COARSE_SCAN_PROMPT_KEY]["filename"],
            "trigger_coarse_scan.txt",
        )

        messages = render_trigger_prompt_messages(
            TRIGGER_COARSE_SCAN_PROMPT_KEY,
            prompts[TRIGGER_COARSE_SCAN_PROMPT_KEY],
            _variables_for(TRIGGER_COARSE_SCAN_PROMPT_KEY),
        )

        self.assertEqual(messages[0]["role"], "user")
        self.assertIn("value:small_summary_batch_text", messages[0]["content"])
        self.assertIn("value:output_json_schema", messages[0]["content"])

    def test_missing_trigger_prompt_variable_reports_stage_and_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("logic.utils.get_global_prompt_cache_dir", return_value=tmpdir):
                prompts = load_trigger_scan_prompt_configs()
        variables = _variables_for(TRIGGER_PRECISE_SCAN_PROMPT_KEY)
        variables.pop("chapter_text_with_paragraph_ids")

        with self.assertRaisesRegex(
            PromptFormattingError,
            "trigger_precise_scan.*chapter_text_with_paragraph_ids",
        ):
            render_trigger_prompt_messages(
                TRIGGER_PRECISE_SCAN_PROMPT_KEY,
                prompts[TRIGGER_PRECISE_SCAN_PROMPT_KEY],
                variables,
            )

    def test_saved_workflow_node_expands_modules_and_can_reset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            update_workflow_prompt_node(
                tmpdir,
                TRIGGER_VERIFICATION_PROMPT_KEY,
                {
                    "messages": [
                        {
                            "id": "system-1",
                            "role": "system",
                            "content": "{{module:general_prepend_prompt}}",
                        },
                        {
                            "id": "user-1",
                            "role": "user",
                            "content": "复核 {first_pass_findings_json} / {output_json_schema}",
                        },
                    ]
                },
            )

            with mock.patch("logic.utils.get_global_prompt_cache_dir", return_value=tmpdir):
                prompts = load_trigger_scan_prompt_configs()
            messages = render_trigger_prompt_messages(
                TRIGGER_VERIFICATION_PROMPT_KEY,
                prompts[TRIGGER_VERIFICATION_PROMPT_KEY],
                _variables_for(TRIGGER_VERIFICATION_PROMPT_KEY),
            )

            reset = reset_workflow_prompt_node(tmpdir, TRIGGER_VERIFICATION_PROMPT_KEY)

        self.assertEqual([message["role"] for message in messages], ["system", "user"])
        self.assertIn("核心输出要求", messages[0]["content"])
        self.assertIn("value:first_pass_findings_json", messages[1]["content"])
        self.assertEqual(
            reset.messages[0].content,
            DEFAULT_PROMPTS[TRIGGER_VERIFICATION_PROMPT_KEY]["default"],
        )


if __name__ == "__main__":
    unittest.main()
