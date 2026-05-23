from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from logic.utils import get_summarizer_cache_dir


@dataclass
class ScanState:
    task_id: str
    config_snapshot: Dict[str, Any]
    profile_version: str
    completed_chapters: List[str] = field(default_factory=list)
    stage_state: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanState":
        return cls(
            task_id=str(data.get("task_id", "")),
            config_snapshot=dict(data.get("config_snapshot", {}) or {}),
            profile_version=str(data.get("profile_version", "")),
            completed_chapters=[str(item) for item in data.get("completed_chapters", [])],
            stage_state=dict(data.get("stage_state", {}) or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "config_snapshot": self.config_snapshot,
            "profile_version": self.profile_version,
            "completed_chapters": self.completed_chapters,
            "stage_state": self.stage_state,
        }


class ScanStateStore:
    def __init__(self, novel_folder_path: str | Path, task_id: str):
        self.novel_folder_path = Path(novel_folder_path)
        self.task_id = str(task_id)
        self.path = Path(get_summarizer_cache_dir(str(self.novel_folder_path))) / f"scan_state_{self.task_id}.json"

    def create(self, config_snapshot: Dict[str, Any], profile_version: str) -> ScanState:
        state = ScanState(
            task_id=self.task_id,
            config_snapshot=dict(config_snapshot),
            profile_version=str(profile_version),
        )
        self.save(state)
        return state

    def load(self) -> ScanState | None:
        if not self.path.exists():
            return None
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                return ScanState.from_dict(json.load(handle))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None

    def save(self, state: ScanState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, ensure_ascii=False, indent=2)
        temp_path.replace(self.path)

    def mark_chapter_complete(self, chapter_file: str) -> ScanState:
        state = self.load() or self.create({}, "")
        if chapter_file not in state.completed_chapters:
            state.completed_chapters.append(chapter_file)
        self.save(state)
        return state

    @staticmethod
    def is_compatible(
        state: ScanState | None,
        *,
        config_snapshot: Dict[str, Any],
        profile_version: str,
    ) -> bool:
        if state is None:
            return False
        return (
            state.config_snapshot == dict(config_snapshot)
            and state.profile_version == str(profile_version)
        )

    @staticmethod
    def find_latest_compatible_state(
        novel_folder_path: str | Path,
        *,
        config_snapshot: Dict[str, Any],
        profile_version: str,
    ) -> ScanState | None:
        """Find the latest compatible scan state from all saved states for this project."""
        cache_dir = Path(get_summarizer_cache_dir(str(novel_folder_path)))
        if not cache_dir.exists():
            return None
        best_state: ScanState | None = None
        best_mtime = 0.0
        for state_file in sorted(cache_dir.glob("scan_state_*.json")):
            try:
                mtime = state_file.stat().st_mtime
                if mtime <= best_mtime:
                    continue
                with state_file.open("r", encoding="utf-8") as handle:
                    state = ScanState.from_dict(json.load(handle))
                if ScanStateStore.is_compatible(
                    state,
                    config_snapshot=config_snapshot,
                    profile_version=profile_version,
                ):
                    best_state = state
                    best_mtime = mtime
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
        return best_state

    @staticmethod
    def pending_chapters(
        chapter_files: Iterable[str],
        state: ScanState | None,
        *,
        config_snapshot: Dict[str, Any],
        profile_version: str,
    ) -> List[str]:
        if not ScanStateStore.is_compatible(
            state,
            config_snapshot=config_snapshot,
            profile_version=profile_version,
        ):
            return [str(chapter_file) for chapter_file in chapter_files]
        completed = set(state.completed_chapters)
        return [str(chapter_file) for chapter_file in chapter_files if str(chapter_file) not in completed]
