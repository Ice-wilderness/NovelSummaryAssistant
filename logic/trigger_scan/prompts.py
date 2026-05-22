from __future__ import annotations

from typing import Any, Dict, Mapping

from logic.llm_api import PromptFormattingError, render_prompt_messages
from logic.utils import load_all_prompts_for_run


TRIGGER_COARSE_SCAN_PROMPT_KEY = "trigger_coarse_scan"
TRIGGER_PRECISE_SCAN_PROMPT_KEY = "trigger_precise_scan"
TRIGGER_VERIFICATION_PROMPT_KEY = "trigger_verification"
TRIGGER_AGGREGATION_PROMPT_KEY = "trigger_aggregation"

TRIGGER_SCAN_PROMPT_KEYS = (
    TRIGGER_COARSE_SCAN_PROMPT_KEY,
    TRIGGER_PRECISE_SCAN_PROMPT_KEY,
    TRIGGER_VERIFICATION_PROMPT_KEY,
    TRIGGER_AGGREGATION_PROMPT_KEY,
)

TRIGGER_SCAN_REQUIRED_VARIABLES = {
    TRIGGER_COARSE_SCAN_PROMPT_KEY: {
        "trigger_rules_json",
        "scan_settings_json",
        "small_summary_batch_text",
        "output_json_schema",
    },
    TRIGGER_PRECISE_SCAN_PROMPT_KEY: {
        "trigger_rules_json",
        "scan_settings_json",
        "chapter_text_with_paragraph_ids",
        "maximum_quote_length",
        "skip_advice_setting",
        "output_json_schema",
    },
    TRIGGER_VERIFICATION_PROMPT_KEY: {
        "trigger_rules_json",
        "referenced_paragraph_context",
        "first_pass_findings_json",
        "output_json_schema",
    },
    TRIGGER_AGGREGATION_PROMPT_KEY: {
        "findings_json",
        "scan_settings_json",
        "output_json_schema",
    },
}


def required_trigger_prompt_variables(prompt_key: str) -> list[str]:
    if prompt_key not in TRIGGER_SCAN_REQUIRED_VARIABLES:
        raise PromptFormattingError(f"未知的雷点扫描提示词节点: {prompt_key}")
    return sorted(TRIGGER_SCAN_REQUIRED_VARIABLES[prompt_key])


def load_trigger_scan_prompt_configs() -> Dict[str, Dict[str, Any]]:
    prompts = load_all_prompts_for_run()
    missing = [key for key in TRIGGER_SCAN_PROMPT_KEYS if key not in prompts]
    if missing:
        raise PromptFormattingError(
            "加载雷点扫描提示词失败，缺少节点: " + ", ".join(missing)
        )
    return {key: prompts[key] for key in TRIGGER_SCAN_PROMPT_KEYS}


def render_trigger_prompt_messages(
    prompt_key: str,
    prompt_config: Mapping[str, Any],
    variables: Mapping[str, Any],
) -> list[dict[str, str]]:
    required_variables = TRIGGER_SCAN_REQUIRED_VARIABLES.get(prompt_key)
    if required_variables is None:
        raise PromptFormattingError(f"未知的雷点扫描提示词节点: {prompt_key}")

    missing = sorted(name for name in required_variables if name not in variables)
    if missing:
        raise PromptFormattingError(
            f"渲染雷点扫描提示词 '{prompt_key}' 时缺少变量: "
            + ", ".join(missing)
        )

    return render_prompt_messages(dict(prompt_config), dict(variables))
