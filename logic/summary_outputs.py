import os
from typing import Any


SUMMARY_OUTPUT_FORMATS = {"md", "txt"}
SUMMARY_OUTPUT_SUFFIXES = {".md", ".txt"}


def normalize_summary_output_format(value: Any, default: str = "md") -> str:
    normalized = str(value or default).strip().lower().lstrip(".")
    if normalized == "markdown":
        normalized = "md"
    if normalized not in SUMMARY_OUTPUT_FORMATS:
        raise ValueError("summary_output_format must be one of: md, txt")
    return normalized


def is_summary_output_filename(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in SUMMARY_OUTPUT_SUFFIXES


def summary_output_filename(task_name: str, output_format: str = "md") -> str:
    stem = os.path.splitext(os.path.basename(task_name))[0]
    return f"{stem}.{normalize_summary_output_format(output_format)}"


def summary_output_path(directory: str, task_name: str, output_format: str = "md") -> str:
    return os.path.join(directory, summary_output_filename(task_name, output_format))


def find_existing_summary_output_file(directory: str, task_name: str) -> str:
    stem = os.path.splitext(os.path.basename(task_name))[0]
    if not os.path.isdir(directory):
        return ""
    for suffix in (".md", ".txt"):
        candidate = os.path.join(directory, f"{stem}{suffix}")
        if os.path.isfile(candidate):
            return candidate
    return ""


def summary_output_peer_exists(filepath: str) -> bool:
    directory = os.path.dirname(filepath)
    task_name = os.path.basename(filepath)
    return bool(find_existing_summary_output_file(directory, task_name))
