from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from webui_backend.file_services import safe_filename


WORKFLOW_EXPORT_SUBDIRS = {
    "novel_summary": "novel-summary",
    "article_summary": "article-summary",
    "custom_summary": "custom-summary",
    "chapter_split": "chapter-split",
}
SUMMARY_OUTPUT_SUFFIXES = {".txt", ".md"}


def current_timestamp() -> float:
    return time.time()


def sanitize_project_name(project_name: str, fallback: str = "project") -> tuple[str, str]:
    display_name = project_name.strip() or fallback
    slug = safe_filename(display_name, max_length=90).strip(" ._")
    if not slug:
        slug = safe_filename(fallback, max_length=90).strip(" ._")
    if not slug:
        slug = f"project-{int(current_timestamp())}"
    return display_name, slug


def workflow_export_subdir(workflow_type: str) -> str:
    return WORKFLOW_EXPORT_SUBDIRS.get(workflow_type, safe_filename(workflow_type, max_length=60))


def read_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json_file(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def count_text_files(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return len([item for item in path.glob("*.txt") if item.is_file()])


def text_file_names(path: Path) -> set[str]:
    if not path.exists() or not path.is_dir():
        return set()
    return {item.name for item in path.glob("*.txt") if item.is_file()}


def summary_file_paths(path: Path) -> List[Path]:
    if not path.exists() or not path.is_dir():
        return []
    return [
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in SUMMARY_OUTPUT_SUFFIXES
    ]


def summary_file_stems(path: Path) -> set[str]:
    return {item.stem for item in summary_file_paths(path)}


def count_summary_files(path: Path) -> int:
    return len(summary_file_paths(path))
