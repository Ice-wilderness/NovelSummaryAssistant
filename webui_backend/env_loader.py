from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Mapping


def default_env_path() -> Path:
    return Path(__file__).resolve().parents[1] / ".env"


def _strip_inline_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
            continue
        if char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.strip()


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        quote = value[0]
        value = value[1:-1]
        if quote == "'":
            return value
        return value.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
    return value


def load_dotenv_values(filepath: str | Path | None = None) -> Dict[str, str]:
    env_path = Path(filepath) if filepath is not None else default_env_path()
    if not env_path.exists():
        return {}

    values: Dict[str, str] = {}
    try:
        lines = env_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return {}

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _unquote(_strip_inline_comment(value.strip()))
    return values


def merged_environment(
    *,
    dotenv_path: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Dict[str, str]:
    merged = load_dotenv_values(dotenv_path)
    merged.update(dict(os.environ if environ is None else environ))
    return merged
