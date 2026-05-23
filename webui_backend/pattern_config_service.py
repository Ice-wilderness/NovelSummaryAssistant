from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config_models import PatternConfig, PatternConfigListResponse


PATTERN_CONFIG_FILENAME = "chapter_patterns.json"
PATTERN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def _current_timestamp() -> float:
    return time.time()


def _new_id() -> str:
    return f"pat_{uuid.uuid4().hex}"


def _validate_pattern_id(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("pattern config id is required")
    if not PATTERN_ID_PATTERN.match(normalized):
        raise ValueError("pattern config id contains invalid characters")
    return normalized


def default_pattern_config_path(runtime_base_path: str | Path) -> Path:
    return Path(runtime_base_path) / PATTERN_CONFIG_FILENAME


# ── 默认预设配置 ──────────────────────────────────────────────

def _builtin_default_raw_pattern() -> str:
    return r"第\s*[一二三四五六七八九十百千万亿零\d]+\s*(?:章|节|回)"


def _build_default_presets() -> List[PatternConfig]:
    now = _current_timestamp()
    return [
        PatternConfig(
            id="preset_default_cn_chapter",
            name="默认-第X章(节|回)",
            regex_mode="raw",
            pattern=_builtin_default_raw_pattern(),
            description="匹配中文小说常见的章节标题格式：第X章、第X节、第X回，支持中文数字和阿拉伯数字",
            is_preset=True,
            created_at=now,
            updated_at=now,
        ),
    ]


# ── Service ───────────────────────────────────────────────────

class PatternConfigService:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        self._configs: Optional[List[PatternConfig]] = None

    @property
    def configs(self) -> List[PatternConfig]:
        if self._configs is None:
            self._configs = self._load_configs()
        return self._configs

    def _load_configs(self) -> List[PatternConfig]:
        if not self.config_path.exists():
            presets = _build_default_presets()
            self._save_configs(presets)
            return presets
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            presets = _build_default_presets()
            self._save_configs(presets)
            return presets
        if not isinstance(raw, list):
            presets = _build_default_presets()
            self._save_configs(presets)
            return presets
        configs = [PatternConfig.from_dict(item) for item in raw if isinstance(item, dict)]
        if not configs:
            presets = _build_default_presets()
            self._save_configs(presets)
            return presets
        return configs

    def _save_configs(self, configs: List[PatternConfig]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = [cfg.to_dict() for cfg in configs]
        tmp_path = self.config_path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.config_path)

    def list_configs(self) -> PatternConfigListResponse:
        return PatternConfigListResponse(items=list(self.configs))

    def get(self, config_id: str) -> PatternConfig:
        safe_id = _validate_pattern_id(config_id)
        for cfg in self.configs:
            if cfg.id == safe_id:
                return cfg
        raise ValueError(f"正则配置不存在：{safe_id}")

    def create(self, name: str, pattern: str, regex_mode: str = "raw", description: str = "") -> PatternConfig:
        now = _current_timestamp()
        cfg = PatternConfig(
            id=_new_id(),
            name=name.strip(),
            regex_mode=regex_mode,
            pattern=pattern,
            description=description.strip(),
            is_preset=False,
            created_at=now,
            updated_at=now,
        )
        cfg.validate()
        configs = list(self.configs)
        configs.append(cfg)
        self._save_configs(configs)
        self._configs = configs
        return cfg

    def update(self, config_id: str, *, name: str = "", pattern: str = "", regex_mode: str = "", description: str = "") -> PatternConfig:
        cfg = self.get(config_id)
        if name.strip():
            cfg.name = name.strip()
        if pattern:
            cfg.pattern = pattern
        if regex_mode:
            from .config_models import _coerce_pattern_regex_mode
            cfg.regex_mode = _coerce_pattern_regex_mode(regex_mode)
        if description.strip():
            cfg.description = description.strip()
        cfg.validate()
        cfg.touch()
        configs = list(self.configs)
        for i, item in enumerate(configs):
            if item.id == cfg.id:
                configs[i] = cfg
                break
        self._save_configs(configs)
        self._configs = configs
        return cfg

    def delete(self, config_id: str) -> None:
        cfg = self.get(config_id)
        if cfg.is_preset:
            raise ValueError("预设配置不可删除")
        configs = [item for item in self.configs if item.id != cfg.id]
        self._save_configs(configs)
        self._configs = configs

    def import_configs(self, raw_data: Any) -> List[PatternConfig]:
        items: List[Dict[str, Any]] = []
        if isinstance(raw_data, list):
            items = [item for item in raw_data if isinstance(item, dict)]
        elif isinstance(raw_data, dict):
            items = [raw_data]

        if not items:
            raise ValueError("导入数据中没有有效的配置项")

        imported: List[PatternConfig] = []
        existing_names = {cfg.name.casefold() for cfg in self.configs}
        now = _current_timestamp()

        for item in items:
            name = str(item.get("name", "")).strip()
            if not name:
                raise ValueError("导入的配置项缺少名称")
            cfg = PatternConfig(
                id=_new_id(),
                name=name,
                regex_mode=str(item.get("regex_mode", "raw")).strip(),
                pattern=str(item.get("pattern", "")),
                description=str(item.get("description", "")),
                is_preset=False,
                created_at=now,
                updated_at=now,
            )
            cfg.validate()
            if cfg.name.casefold() in existing_names:
                continue
            imported.append(cfg)
            existing_names.add(cfg.name.casefold())

        if not imported:
            raise ValueError("所有导入的配置名称均已存在，跳过导入")

        configs = list(self.configs)
        configs.extend(imported)
        self._save_configs(configs)
        self._configs = configs
        return imported

    def export_config(self, config_id: str) -> Dict[str, Any]:
        cfg = self.get(config_id)
        return cfg.to_export_dict()

    def resolve_pattern_regex(self, config_id: str) -> str:
        """返回可直接用于编译的正则字符串（raw 模式可能经过自动包裹处理）。"""
        cfg = self.get(config_id)
        if cfg.regex_mode == "simple":
            from splitters.regex_strategy import build_regex_from_simple_pattern
            return build_regex_from_simple_pattern(cfg.pattern)
        else:
            return self._wrap_raw_if_needed(cfg.pattern)

    @staticmethod
    def _wrap_raw_if_needed(pattern: str) -> str:
        """若 raw 模式的正则不含捕获组，自动包裹生成 group(1) 和 group(2)。"""
        try:
            compiled = re.compile(pattern)
        except re.error:
            raise ValueError(f"正则表达式语法无效: {pattern}")
        if compiled.groups == 0:
            return rf"^\s*(({pattern}).*)"
        return pattern
