from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List

from logic.prompts import DEFAULT_PROMPTS

from .config_models import ApiConfig, PromptTemplate


def _default_display_name(index: int) -> str:
    return f"API {index + 1}"


def _with_default_display_name(item: Dict[str, Any], index: int) -> Dict[str, Any]:
    if item.get("display_name") or item.get("api_key_name") or item.get("name"):
        return item
    return {**item, "display_name": _default_display_name(index)}


def _validate_unique_display_names(configs: Iterable[ApiConfig]) -> None:
    seen: set[str] = set()
    for config in configs:
        name = config.display_name.strip()
        if not name:
            raise ValueError("API 预设名称不能为空")
        key = name.casefold()
        if key in seen:
            raise ValueError(f"API 预设名称不能重复：{name}")
        seen.add(key)


def load_api_configs(filepath: str) -> List[ApiConfig]:
    if not os.path.exists(filepath):
        return [ApiConfig.from_dict({"display_name": _default_display_name(0)})]
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_configs = json.load(f)
    except (json.JSONDecodeError, OSError):
        return [ApiConfig.from_dict({"display_name": _default_display_name(0)})]
    if not isinstance(raw_configs, list):
        return [ApiConfig.from_dict({"display_name": _default_display_name(0)})]
    return [
        ApiConfig.from_dict(_with_default_display_name(item, index))
        for index, item in enumerate(raw_configs)
        if isinstance(item, dict)
    ]


def save_api_configs(filepath: str, configs: Iterable[ApiConfig]) -> None:
    configs = list(configs)
    _validate_unique_display_names(configs)
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
    _validate_unique_display_names(prepared)
    return prepared


def public_api_configs(configs: Iterable[ApiConfig]) -> List[Dict]:
    return [config.to_public_dict() for config in configs]


def resolve_api_config(config: ApiConfig, environ: Dict[str, str] | None = None) -> Dict:
    data = config.to_storage_dict()
    data["key"] = config.effective_key(environ)
    data["api_key_name"] = config.display_name or config.id
    data["display_name"] = config.display_name or config.id
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
