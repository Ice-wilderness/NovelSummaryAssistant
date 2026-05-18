from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List

from logic.prompts import DEFAULT_PROMPTS

from .config_models import ApiConfig, PromptTemplate


def load_api_configs(filepath: str) -> List[ApiConfig]:
    if not os.path.exists(filepath):
        return [ApiConfig.from_dict({})]
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_configs = json.load(f)
    except (json.JSONDecodeError, OSError):
        return [ApiConfig.from_dict({})]
    if not isinstance(raw_configs, list):
        return [ApiConfig.from_dict({})]
    return [ApiConfig.from_dict(item) for item in raw_configs if isinstance(item, dict)]


def save_api_configs(filepath: str, configs: Iterable[ApiConfig]) -> None:
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    data = [config.to_storage_dict() for config in configs]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _looks_like_masked_secret(value: str) -> bool:
    return bool(value) and set(value[:-4] or value) == {"*"}


def prepare_api_configs_for_save(
    raw_items: Iterable[Dict[str, Any]],
    existing_configs: Iterable[ApiConfig],
) -> List[ApiConfig]:
    existing_by_id = {config.id: config for config in existing_configs}
    prepared: List[ApiConfig] = []
    for item in raw_items:
        config = ApiConfig.from_dict(item)
        existing = existing_by_id.get(config.id)
        should_preserve_key = (
            existing is not None
            and bool(item.get("has_key"))
            and (not config.key or _looks_like_masked_secret(config.key))
        )
        if should_preserve_key:
            config.key = existing.key
        prepared.append(config)
    return prepared


def public_api_configs(configs: Iterable[ApiConfig]) -> List[Dict]:
    return [config.to_public_dict() for config in configs]


def resolve_api_config(config: ApiConfig, environ: Dict[str, str] | None = None) -> Dict:
    data = config.to_storage_dict()
    data["key"] = config.effective_key(environ)
    return data


def _prompt_path(cache_dir: str, filename: str) -> str:
    return os.path.join(cache_dir, filename)


def load_prompt_templates(cache_dir: str) -> List[PromptTemplate]:
    templates = []
    for key, config in DEFAULT_PROMPTS.items():
        filename = config["filename"]
        default_text = config["default"]
        text = default_text
        filepath = _prompt_path(cache_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                text = default_text
        templates.append(
            PromptTemplate(
                key=key,
                filename=filename,
                text=text,
                default_text=default_text,
            )
        )
    return templates


def save_prompt_template(cache_dir: str, template: PromptTemplate) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    with open(_prompt_path(cache_dir, template.filename), "w", encoding="utf-8") as f:
        f.write(template.text)


def reset_prompt_template(cache_dir: str, template: PromptTemplate) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    with open(_prompt_path(cache_dir, template.filename), "w", encoding="utf-8") as f:
        f.write(template.default_text)
