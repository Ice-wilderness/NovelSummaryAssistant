from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, List

from config import TASK_ID_FILENAME
from logic import utils
from logic.article_summary_logic import ARTICLE_STATE_FILENAME


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_runtime_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.argv[0]).resolve().parent
    return get_project_root()


def normalize_user_path(path_value: str) -> Path:
    return Path(path_value).expanduser().resolve()


def get_summarizer_cache_dir(source_folder_path: str) -> Path:
    return Path(utils.get_summarizer_cache_dir(str(source_folder_path)))


def get_task_id_path(source_folder_path: str) -> Path:
    return get_summarizer_cache_dir(source_folder_path) / TASK_ID_FILENAME


def get_article_state_path(source_folder_path: str) -> Path:
    return get_summarizer_cache_dir(source_folder_path) / ARTICLE_STATE_FILENAME


def get_prompt_cache_dir(project_root: Path | None = None) -> Path:
    base = get_project_root() if project_root is None else Path(project_root)
    return base / "prompt_cache"


def ensure_prompt_cache_dir(project_root: Path | None = None) -> Path:
    path = get_prompt_cache_dir(project_root)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def read_text_file_async(filepath: str) -> str:
    return await utils.read_file_content_robustly_async(filepath)


def read_text_file(filepath: str) -> str:
    return utils.read_file_content_robustly(filepath)


def safe_filename(filename: str, max_length: int = 150) -> str:
    return utils.sanitize_filename(filename, max_length=max_length)


def natural_sort_key(filename: str):
    return utils.natural_sort_key(filename)


def sort_naturally(paths: Iterable[str]) -> List[str]:
    return sorted(paths, key=natural_sort_key)
