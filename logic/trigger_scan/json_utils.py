from __future__ import annotations

import json
import re
from typing import Any


class TriggerScanJsonError(ValueError):
    pass


def extract_json_text(model_output: str) -> str:
    text = str(model_output or "").strip()
    if not text:
        raise TriggerScanJsonError("model output is empty")

    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fence:
        return fence.group(1).strip()

    first_object = text.find("{")
    first_array = text.find("[")
    starts = [position for position in [first_object, first_array] if position >= 0]
    if not starts:
        raise TriggerScanJsonError("model output does not contain JSON")
    start = min(starts)
    end = max(text.rfind("}"), text.rfind("]"))
    if end < start:
        raise TriggerScanJsonError("model output contains incomplete JSON")
    return text[start:end + 1].strip()


def parse_json_payload(model_output: str) -> Any:
    try:
        return json.loads(extract_json_text(model_output))
    except json.JSONDecodeError as exc:
        raise TriggerScanJsonError(f"invalid JSON: {exc}") from exc


def require_json_object(model_output: str) -> dict[str, Any]:
    payload = parse_json_payload(model_output)
    if not isinstance(payload, dict):
        raise TriggerScanJsonError("expected a JSON object")
    return payload


def require_json_list(model_output: str) -> list[Any]:
    payload = parse_json_payload(model_output)
    if isinstance(payload, dict) and isinstance(payload.get("findings"), list):
        return payload["findings"]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    if not isinstance(payload, list):
        raise TriggerScanJsonError("expected a JSON list")
    return payload
