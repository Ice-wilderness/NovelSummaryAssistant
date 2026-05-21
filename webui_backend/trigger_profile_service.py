from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from .trigger_models import (
    TriggerProfile,
    TriggerRule,
    TriggerRuleGroup,
    builtin_trigger_profile,
)


PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def current_timestamp() -> float:
    return time.time()


def default_trigger_profile_dir(runtime_base_path: str | Path) -> Path:
    return Path(runtime_base_path) / "workspace" / "trigger_profiles"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _validate_file_id(value: str, field_name: str = "id") -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if not PROFILE_ID_PATTERN.match(normalized):
        raise ValueError(f"{field_name} contains invalid characters")
    return normalized


class TriggerProfileService:
    def __init__(
        self,
        runtime_base_path: str | Path | None = None,
        *,
        profile_dir: str | Path | None = None,
    ) -> None:
        if profile_dir is None:
            if runtime_base_path is None:
                raise ValueError("runtime_base_path or profile_dir is required")
            self.profile_dir = default_trigger_profile_dir(runtime_base_path)
        else:
            self.profile_dir = Path(profile_dir)

    def ensure_storage_dir(self) -> Path:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        return self.profile_dir

    def profile_path(self, profile_id: str) -> Path:
        safe_id = _validate_file_id(profile_id, "profile_id")
        return self.ensure_storage_dir() / f"{safe_id}.json"

    def list_profiles(self) -> List[TriggerProfile]:
        self._ensure_default_profile()
        profiles: List[TriggerProfile] = []
        for path in self.ensure_storage_dir().glob("*.json"):
            try:
                profiles.append(self._read_profile_file(path))
            except ValueError:
                continue
        return sorted(
            profiles,
            key=lambda profile: (profile.updated_at, profile.name.casefold()),
            reverse=True,
        )

    def load_profile(self, profile_id: str) -> TriggerProfile:
        path = self.profile_path(profile_id)
        if not path.exists():
            raise ValueError(f"Unknown trigger profile: {profile_id}")
        return self._read_profile_file(path)

    def create_profile(self, payload: Dict[str, Any]) -> TriggerProfile:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("profile name is required")
        now = current_timestamp()
        use_template = bool(payload.get("from_template", True))
        if use_template:
            profile = builtin_trigger_profile(timestamp=now)
            profile.id = _new_id("profile")
            profile.name = name
            profile.description = str(payload.get("description", profile.description))
            profile.created_at = now
            profile.updated_at = now
        else:
            profile = TriggerProfile(
                id=_new_id("profile"),
                name=name,
                description=str(payload.get("description", "")),
                created_at=now,
                updated_at=now,
            )
        self.save_profile(profile)
        return profile

    def update_profile(self, profile_id: str, payload: Dict[str, Any]) -> TriggerProfile:
        profile = self.load_profile(profile_id)
        if "name" in payload:
            profile.name = str(payload.get("name") or "").strip()
        if "description" in payload:
            profile.description = str(payload.get("description", ""))
        if "rule_groups" in payload:
            profile.rule_groups = [
                TriggerRuleGroup.from_dict(item)
                for item in payload.get("rule_groups", [])
                if isinstance(item, dict)
            ]
        if "rules" in payload:
            profile.rules = [
                TriggerRule.from_dict(item)
                for item in payload.get("rules", [])
                if isinstance(item, dict)
            ]
        self._touch(profile)
        self.save_profile(profile)
        return profile

    def duplicate_profile(self, profile_id: str, payload: Dict[str, Any] | None = None) -> TriggerProfile:
        source = self.load_profile(profile_id)
        payload = payload or {}
        now = current_timestamp()
        duplicate = TriggerProfile.from_dict(source.to_dict())
        duplicate.id = _new_id("profile")
        duplicate.name = str(payload.get("name") or f"{source.name} 副本").strip()
        duplicate.description = str(payload.get("description", source.description))
        duplicate.created_at = now
        duplicate.updated_at = now
        self.save_profile(duplicate)
        return duplicate

    def delete_profile(self, profile_id: str) -> None:
        path = self.profile_path(profile_id)
        if not path.exists():
            raise ValueError(f"Unknown trigger profile: {profile_id}")
        path.unlink()

    def add_rule_group(self, profile_id: str, payload: Dict[str, Any]) -> TriggerProfile:
        profile = self.load_profile(profile_id)
        group = TriggerRuleGroup.from_dict(
            {
                "id": payload.get("id") or _new_id("group"),
                "name": payload.get("name"),
                "rules": payload.get("rules", []),
            }
        )
        profile.rule_groups.append(group)
        self._touch(profile)
        self.save_profile(profile)
        return profile

    def update_rule_group(
        self,
        profile_id: str,
        group_id: str,
        payload: Dict[str, Any],
    ) -> TriggerProfile:
        profile = self.load_profile(profile_id)
        group = self._find_group(profile, group_id)
        if "name" in payload:
            group.name = str(payload.get("name") or "").strip()
        if "rules" in payload:
            group.rules = [rule_id for rule_id in payload.get("rules", []) if self._has_rule(profile, str(rule_id))]
        self._touch(profile)
        self.save_profile(profile)
        return profile

    def delete_rule_group(self, profile_id: str, group_id: str) -> TriggerProfile:
        profile = self.load_profile(profile_id)
        if any(rule.group_id == group_id for rule in profile.rules):
            raise ValueError("Cannot delete a rule group that still contains rules")
        original_count = len(profile.rule_groups)
        profile.rule_groups = [group for group in profile.rule_groups if group.id != group_id]
        if len(profile.rule_groups) == original_count:
            raise ValueError(f"Unknown trigger rule group: {group_id}")
        self._touch(profile)
        self.save_profile(profile)
        return profile

    def add_rule(self, profile_id: str, payload: Dict[str, Any]) -> TriggerProfile:
        profile = self.load_profile(profile_id)
        rule = TriggerRule.from_dict(
            {
                **payload,
                "id": payload.get("id") or _new_id("rule"),
            }
        )
        self._require_group(profile, rule.group_id)
        profile.rules.append(rule)
        group = self._find_group(profile, rule.group_id)
        if rule.id not in group.rules:
            group.rules.append(rule.id)
        self._touch(profile)
        self.save_profile(profile)
        return profile

    def update_rule(
        self,
        profile_id: str,
        rule_id: str,
        payload: Dict[str, Any],
    ) -> TriggerProfile:
        profile = self.load_profile(profile_id)
        rule = self._find_rule(profile, rule_id)
        previous_group_id = rule.group_id
        merged = {**rule.to_dict(), **payload, "id": rule.id}
        updated = TriggerRule.from_dict(merged)
        self._require_group(profile, updated.group_id)
        profile.rules = [updated if item.id == rule_id else item for item in profile.rules]
        if previous_group_id != updated.group_id:
            self._remove_rule_from_groups(profile, updated.id)
            group = self._find_group(profile, updated.group_id)
            group.rules.append(updated.id)
        self._touch(profile)
        self.save_profile(profile)
        return profile

    def delete_rule(self, profile_id: str, rule_id: str) -> TriggerProfile:
        profile = self.load_profile(profile_id)
        original_count = len(profile.rules)
        profile.rules = [rule for rule in profile.rules if rule.id != rule_id]
        if len(profile.rules) == original_count:
            raise ValueError(f"Unknown trigger rule: {rule_id}")
        self._remove_rule_from_groups(profile, rule_id)
        self._touch(profile)
        self.save_profile(profile)
        return profile

    def profile_snapshot(self, profile_id: str) -> Dict[str, Any]:
        profile = self.load_profile(profile_id)
        snapshot = profile.to_dict()
        snapshot["version"] = self.profile_version(profile)
        return snapshot

    def profile_version(self, profile: TriggerProfile) -> str:
        return f"{profile.id}:{profile.updated_at:.6f}"

    def save_profile(self, profile: TriggerProfile) -> None:
        profile.validate()
        path = self.profile_path(profile.id)
        data = profile.to_dict()
        tmp_path = path.with_suffix(".json.tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        tmp_path.replace(path)

    def _ensure_default_profile(self) -> None:
        directory = self.ensure_storage_dir()
        if any(directory.glob("*.json")):
            return
        self.save_profile(builtin_trigger_profile(timestamp=current_timestamp()))

    def _read_profile_file(self, path: Path) -> TriggerProfile:
        try:
            with path.open("r", encoding="utf-8") as handle:
                raw_data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid trigger profile file: {path}") from exc
        if not isinstance(raw_data, dict):
            raise ValueError(f"Invalid trigger profile file: {path}")
        profile = TriggerProfile.from_dict(raw_data)
        profile.validate()
        return profile

    def _touch(self, profile: TriggerProfile) -> None:
        if not profile.created_at:
            profile.created_at = current_timestamp()
        profile.updated_at = max(current_timestamp(), profile.updated_at + 0.000001)

    def _find_group(self, profile: TriggerProfile, group_id: str) -> TriggerRuleGroup:
        for group in profile.rule_groups:
            if group.id == group_id:
                return group
        raise ValueError(f"Unknown trigger rule group: {group_id}")

    def _require_group(self, profile: TriggerProfile, group_id: str) -> None:
        self._find_group(profile, group_id)

    def _find_rule(self, profile: TriggerProfile, rule_id: str) -> TriggerRule:
        for rule in profile.rules:
            if rule.id == rule_id:
                return rule
        raise ValueError(f"Unknown trigger rule: {rule_id}")

    def _has_rule(self, profile: TriggerProfile, rule_id: str) -> bool:
        return any(rule.id == rule_id for rule in profile.rules)

    def _remove_rule_from_groups(self, profile: TriggerProfile, rule_id: str) -> None:
        for group in profile.rule_groups:
            group.rules = [item for item in group.rules if item != rule_id]
