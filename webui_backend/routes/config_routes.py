from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException

from logic.llm_api import fetch_available_models

from ..config_service import (
    delete_prompt_module,
    load_api_configs,
    load_api_configs_with_warnings,
    load_prompt_templates,
    load_user_settings,
    load_user_settings_with_warnings,
    load_workflow_prompt_config,
    prepare_api_configs_for_save,
    prepare_user_settings_for_save,
    public_api_configs,
    reset_prompt_template,
    reset_workflow_prompt_node,
    resolve_api_config,
    save_api_configs,
    save_prompt_template,
    save_user_settings,
    update_workflow_prompt_node,
    upsert_prompt_module,
)
from .context import RouteContext


def _get_prompt_template(cache_dir: Path, prompt_key: str):
    for template in load_prompt_templates(str(cache_dir)):
        if template.key == prompt_key:
            return template
    raise HTTPException(status_code=404, detail=f"Unknown prompt key: {prompt_key}")


def register_config_routes(ctx: RouteContext) -> None:
    app = ctx.app

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/config/api")
    async def get_api_config():
        result = load_api_configs_with_warnings(str(app.state.api_config_path))
        return {
            "items": public_api_configs(result.items),
            "warnings": [warning.to_dict() for warning in result.warnings],
        }

    @app.post("/api/config/api")
    async def save_api_config(payload: List[Dict[str, Any]]):
        existing_configs = load_api_configs(str(app.state.api_config_path))
        try:
            configs = prepare_api_configs_for_save(payload, existing_configs)
            save_api_configs(str(app.state.api_config_path), configs)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"items": public_api_configs(configs)}

    @app.get("/api/settings")
    async def get_user_settings():
        result = load_user_settings_with_warnings(str(app.state.user_settings_path))
        data = result.settings.to_dict()
        data["warnings"] = [warning.to_dict() for warning in result.warnings]
        return data

    @app.post("/api/settings")
    async def update_user_settings(payload: Dict[str, Any]):
        try:
            settings = prepare_user_settings_for_save(payload)
            save_user_settings(str(app.state.user_settings_path), settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return settings.to_dict()

    @app.delete("/api/settings/default-export-directory")
    async def clear_default_export_directory():
        settings = load_user_settings(str(app.state.user_settings_path))
        settings.default_export_directory = ""
        save_user_settings(str(app.state.user_settings_path), settings)
        return settings.to_dict()

    @app.get("/api/prompts")
    async def get_prompts():
        templates = load_prompt_templates(str(app.state.prompt_cache_dir))
        workflow_config = load_workflow_prompt_config(str(app.state.prompt_cache_dir))
        return {
            "items": [template.to_dict() for template in templates],
            "workflow_config": workflow_config.to_dict(),
        }

    @app.post("/api/prompts/modules")
    async def save_prompt_module(payload: Dict[str, Any]):
        try:
            config = upsert_prompt_module(str(app.state.prompt_cache_dir), payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return config.to_dict()

    @app.delete("/api/prompts/modules/{module_id}")
    async def remove_prompt_module(module_id: str):
        try:
            config = delete_prompt_module(str(app.state.prompt_cache_dir), module_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return config.to_dict()

    @app.post("/api/prompts/{prompt_key}")
    async def save_prompt(prompt_key: str, payload: Dict[str, Any]):
        template = _get_prompt_template(app.state.prompt_cache_dir, prompt_key)
        template.text = str(payload.get("text", ""))
        save_prompt_template(str(app.state.prompt_cache_dir), template)
        return template.to_dict()

    @app.post("/api/prompts/{prompt_key}/reset")
    async def reset_prompt(prompt_key: str):
        template = _get_prompt_template(app.state.prompt_cache_dir, prompt_key)
        reset_prompt_template(str(app.state.prompt_cache_dir), template)
        template.text = template.default_text
        return template.to_dict()

    @app.post("/api/prompts/nodes/{prompt_key}")
    async def save_prompt_node(prompt_key: str, payload: Dict[str, Any]):
        try:
            node = update_workflow_prompt_node(
                str(app.state.prompt_cache_dir),
                prompt_key,
                payload,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return node.to_dict()

    @app.post("/api/prompts/nodes/{prompt_key}/reset")
    async def reset_prompt_node(prompt_key: str):
        try:
            node = reset_workflow_prompt_node(str(app.state.prompt_cache_dir), prompt_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return node.to_dict()

    @app.post("/api/models")
    async def get_models(payload: Dict[str, Any]):
        config = prepare_api_configs_for_save(
            [payload],
            load_api_configs(str(app.state.api_config_path)),
        )[0]
        resolved = resolve_api_config(config)
        if not resolved.get("url") or not resolved.get("key"):
            raise HTTPException(status_code=400, detail="API url and key are required")
        models, error = await fetch_available_models(resolved["url"], resolved["key"])
        if error:
            raise HTTPException(status_code=400, detail=error)
        return {"items": models}
