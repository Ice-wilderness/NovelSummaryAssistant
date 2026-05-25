from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException

from .context import RouteContext


def register_profile_pattern_routes(ctx: RouteContext) -> None:
    app = ctx.app

    @app.get("/api/trigger-profiles")
    async def list_trigger_profiles():
        profiles = ctx.trigger_profile_service().list_profiles()
        return {"items": [profile.to_dict() for profile in profiles]}

    @app.post("/api/trigger-profiles")
    async def create_trigger_profile(payload: Dict[str, Any]):
        try:
            profile = ctx.trigger_profile_service().create_profile(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.post("/api/trigger-profiles/import")
    async def import_trigger_profile(payload: Dict[str, Any]):
        try:
            profile = ctx.trigger_profile_service().import_profile(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.get("/api/trigger-profiles/{profile_id}")
    async def get_trigger_profile(profile_id: str):
        try:
            profile = ctx.trigger_profile_service().load_profile(profile_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return profile.to_dict()

    @app.patch("/api/trigger-profiles/{profile_id}")
    async def update_trigger_profile(profile_id: str, payload: Dict[str, Any]):
        try:
            profile = ctx.trigger_profile_service().update_profile(profile_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.post("/api/trigger-profiles/{profile_id}/duplicate")
    async def duplicate_trigger_profile(profile_id: str, payload: Dict[str, Any] | None = None):
        try:
            profile = ctx.trigger_profile_service().duplicate_profile(profile_id, payload or {})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.delete("/api/trigger-profiles/{profile_id}")
    async def delete_trigger_profile(profile_id: str):
        try:
            ctx.trigger_profile_service().delete_profile(profile_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return {"status": "deleted", "profile_id": profile_id}

    @app.post("/api/trigger-profiles/{profile_id}/groups")
    async def add_trigger_rule_group(profile_id: str, payload: Dict[str, Any]):
        try:
            profile = ctx.trigger_profile_service().add_rule_group(profile_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.patch("/api/trigger-profiles/{profile_id}/groups/{group_id}")
    async def update_trigger_rule_group(
        profile_id: str,
        group_id: str,
        payload: Dict[str, Any],
    ):
        try:
            profile = ctx.trigger_profile_service().update_rule_group(profile_id, group_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.delete("/api/trigger-profiles/{profile_id}/groups/{group_id}")
    async def delete_trigger_rule_group(profile_id: str, group_id: str):
        try:
            profile = ctx.trigger_profile_service().delete_rule_group(profile_id, group_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.post("/api/trigger-profiles/{profile_id}/rules")
    async def add_trigger_rule(profile_id: str, payload: Dict[str, Any]):
        try:
            profile = ctx.trigger_profile_service().add_rule(profile_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.patch("/api/trigger-profiles/{profile_id}/rules/{rule_id}")
    async def update_trigger_rule(
        profile_id: str,
        rule_id: str,
        payload: Dict[str, Any],
    ):
        try:
            profile = ctx.trigger_profile_service().update_rule(profile_id, rule_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.delete("/api/trigger-profiles/{profile_id}/rules/{rule_id}")
    async def delete_trigger_rule(profile_id: str, rule_id: str):
        try:
            profile = ctx.trigger_profile_service().delete_rule(profile_id, rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return profile.to_dict()

    @app.get("/api/patterns")
    async def list_patterns():
        return ctx.pattern_config_service().list_configs().to_dict()

    @app.post("/api/patterns")
    async def create_pattern(payload: Dict[str, Any]):
        try:
            cfg = ctx.pattern_config_service().create(
                name=str(payload.get("name", "")),
                pattern=str(payload.get("pattern", "")),
                regex_mode=str(payload.get("regex_mode", "raw")),
                description=str(payload.get("description", "")),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return cfg.to_dict()

    @app.put("/api/patterns/{config_id}")
    async def update_pattern(config_id: str, payload: Dict[str, Any]):
        try:
            cfg = ctx.pattern_config_service().update(
                config_id,
                name=str(payload.get("name", "")),
                pattern=str(payload.get("pattern", "")),
                regex_mode=str(payload.get("regex_mode", "")),
                description=str(payload.get("description", "")),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return cfg.to_dict()

    @app.delete("/api/patterns/{config_id}")
    async def delete_pattern(config_id: str):
        try:
            ctx.pattern_config_service().delete(config_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"ok": True, "config_id": config_id}

    @app.post("/api/patterns/import")
    async def import_patterns(payload: Dict[str, Any]):
        try:
            imported = ctx.pattern_config_service().import_configs(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"imported_count": len(imported), "items": [cfg.to_dict() for cfg in imported]}

    @app.get("/api/patterns/{config_id}/export")
    async def export_pattern(config_id: str):
        try:
            data = ctx.pattern_config_service().export_config(config_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return data
