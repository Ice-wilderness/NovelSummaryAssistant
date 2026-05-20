from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from logic.prompts import DEFAULT_PROMPTS

from .config_models import (
    ApiConfig,
    PromptMessage,
    PromptModule,
    PromptNode,
    PromptTemplate,
    UserSettings,
    WorkflowPromptConfig,
)
from .prompt_workflows import create_default_workflow_prompt_config, extract_prompt_variables


WORKFLOW_PROMPT_CONFIG_FILENAME = "prompt_workflows.json"
USER_SETTINGS_FILENAME = "user_settings.json"
MODULE_REFERENCE_PATTERN = re.compile(r"\{\{\s*module:([A-Za-z0-9_-]+)\s*\}\}")


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


def load_user_settings(filepath: str) -> UserSettings:
    if not os.path.exists(filepath):
        return UserSettings()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_settings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return UserSettings()
    if not isinstance(raw_settings, dict):
        return UserSettings()
    return UserSettings.from_dict(raw_settings)


def normalize_default_export_directory(path_value: str) -> str:
    value = path_value.strip()
    if not value:
        return ""
    path = Path(value).expanduser().resolve(strict=False)
    if path.exists() and not path.is_dir():
        raise ValueError("默认导出目录不能是文件")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError(f"默认导出目录不可用：{path}") from exc
    return str(path)


def prepare_user_settings_for_save(raw_settings: Dict[str, Any]) -> UserSettings:
    raw_minimum_output_characters = raw_settings.get("minimum_output_characters", 0)
    try:
        int(raw_minimum_output_characters)
    except (TypeError, ValueError) as exc:
        raise ValueError("最少输出字数必须是非负整数") from exc
    settings = UserSettings.from_dict(raw_settings)
    settings.default_export_directory = normalize_default_export_directory(
        settings.default_export_directory
    )
    if settings.minimum_output_characters < 0:
        raise ValueError("最少输出字数不能小于 0")
    return settings


def save_user_settings(filepath: str, settings: UserSettings) -> None:
    settings.default_export_directory = normalize_default_export_directory(
        settings.default_export_directory
    )
    if settings.minimum_output_characters < 0:
        raise ValueError("最少输出字数不能小于 0")
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)


def _prompt_path(cache_dir: str, filename: str) -> str:
    return os.path.join(cache_dir, filename)


def _workflow_prompt_config_path(cache_dir: str) -> str:
    return os.path.join(cache_dir, WORKFLOW_PROMPT_CONFIG_FILENAME)


def _load_legacy_prompt_text(cache_dir: str, filename: str, default_text: str) -> tuple[str, bool]:
    filepath = _prompt_path(cache_dir, filename)
    if not os.path.exists(filepath):
        return default_text, False
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read(), True
    except OSError:
        return default_text, False


def load_workflow_prompt_config(cache_dir: str) -> WorkflowPromptConfig:
    structured_path = _workflow_prompt_config_path(cache_dir)
    if os.path.exists(structured_path):
        try:
            with open(structured_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            if isinstance(raw_data, dict):
                config = WorkflowPromptConfig.from_dict(raw_data)
                config.source = "structured"
                return config
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    config = create_default_workflow_prompt_config()
    found_legacy = False
    prompt_defaults = {
        key: {
            "filename": str(value["filename"]),
            "default": str(value["default"]),
        }
        for key, value in DEFAULT_PROMPTS.items()
    }
    for workflow in config.workflows:
        for node in workflow.nodes:
            prompt_default = prompt_defaults.get(node.prompt_key)
            if not prompt_default:
                continue
            text, found = _load_legacy_prompt_text(
                cache_dir,
                prompt_default["filename"],
                prompt_default["default"],
            )
            found_legacy = found_legacy or found
            if node.messages:
                node.messages[0].content = text
    for module in config.modules:
        prompt_default = prompt_defaults.get(module.id)
        if not prompt_default:
            continue
        text, found = _load_legacy_prompt_text(
            cache_dir,
            prompt_default["filename"],
            prompt_default["default"],
        )
        found_legacy = found_legacy or found
        module.content = text
        if module.messages:
            module.messages[0].content = text
    config.source = "legacy" if found_legacy else "defaults"
    return config


def save_workflow_prompt_config(cache_dir: str, config: WorkflowPromptConfig) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    validate_workflow_prompt_modules(config)
    data = config.to_dict()
    data["source"] = "structured"
    with open(_workflow_prompt_config_path(cache_dir), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_workflow_prompt_node(config: WorkflowPromptConfig, prompt_key: str) -> PromptNode:
    for workflow in config.workflows:
        for node in workflow.nodes:
            if node.prompt_key == prompt_key or node.id == prompt_key:
                return node
    raise ValueError(f"Unknown prompt node: {prompt_key}")


def _clone_prompt_messages(messages: Iterable[PromptMessage]) -> List[PromptMessage]:
    return [PromptMessage.from_dict(message.to_dict()) for message in messages]


def extract_module_references(text: str) -> List[str]:
    return sorted(set(MODULE_REFERENCE_PATTERN.findall(text)))


def collect_prompt_module_references(config: WorkflowPromptConfig) -> Dict[str, List[str]]:
    references: Dict[str, List[str]] = {}
    for workflow in config.workflows:
        for node in workflow.nodes:
            for message in node.messages:
                if message.kind == "module":
                    references.setdefault(message.module_id, []).append(node.prompt_key)
                for module_id in extract_module_references(message.content):
                    references.setdefault(module_id, []).append(node.prompt_key)
    return references


def validate_workflow_prompt_modules(config: WorkflowPromptConfig) -> None:
    module_ids = {module.id for module in config.modules}
    references = collect_prompt_module_references(config)
    missing = sorted(module_id for module_id in references if module_id not in module_ids)
    if missing:
        raise ValueError(f"Unknown prompt module reference: {', '.join(missing)}")


def upsert_prompt_module(cache_dir: str, payload: Dict[str, Any]) -> WorkflowPromptConfig:
    config = load_workflow_prompt_config(cache_dir)
    module = PromptModule.from_dict(payload)
    for index, existing in enumerate(config.modules):
        if existing.id == module.id:
            if "default_content" not in payload:
                module.default_content = existing.default_content
            config.modules[index] = module
            break
    else:
        config.modules.append(module)
    save_workflow_prompt_config(cache_dir, config)
    return config


def delete_prompt_module(cache_dir: str, module_id: str) -> WorkflowPromptConfig:
    config = load_workflow_prompt_config(cache_dir)
    references = collect_prompt_module_references(config)
    if module_id in references:
        nodes = ", ".join(sorted(set(references[module_id])))
        raise ValueError(f"Prompt module '{module_id}' is still used by nodes: {nodes}")
    next_modules = [module for module in config.modules if module.id != module_id]
    if len(next_modules) == len(config.modules):
        raise ValueError(f"Unknown prompt module: {module_id}")
    config.modules = next_modules
    save_workflow_prompt_config(cache_dir, config)
    return config


def update_workflow_prompt_node(
    cache_dir: str,
    prompt_key: str,
    payload: Dict[str, Any],
) -> PromptNode:
    config = load_workflow_prompt_config(cache_dir)
    node = find_workflow_prompt_node(config, prompt_key)
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ValueError("prompt node messages are required")
    node.messages = [PromptMessage.from_dict(item) for item in raw_messages if isinstance(item, dict)]
    if not node.messages:
        raise ValueError("prompt node messages are required")
    combined_text = "\n".join(msg.content for msg in node.messages if msg.content)
    node.variables = extract_prompt_variables(combined_text)
    save_workflow_prompt_config(cache_dir, config)
    return node


def reset_workflow_prompt_node(cache_dir: str, prompt_key: str) -> PromptNode:
    config = load_workflow_prompt_config(cache_dir)
    node = find_workflow_prompt_node(config, prompt_key)
    node.messages = _clone_prompt_messages(node.default_messages)
    combined_text = "\n".join(msg.content for msg in node.messages if msg.content)
    node.variables = extract_prompt_variables(combined_text)
    save_workflow_prompt_config(cache_dir, config)
    return node


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
