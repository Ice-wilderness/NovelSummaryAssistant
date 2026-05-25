from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from .low_state import current_timestamp, read_json_file, workflow_export_subdir, write_json_file


OUTPUT_OWNERSHIP_FILENAME = ".nsa_output_owner.json"
OUTPUT_OWNERSHIP_OWNER = "NovelSummaryAssistant"
OUTPUT_OWNERSHIP_PURPOSE = "managed_project_export_root"


def write_output_ownership(project_export_dir: Path, project_slug: str) -> None:
    ownership_path = project_export_dir / OUTPUT_OWNERSHIP_FILENAME
    existing = read_json_file(ownership_path)
    data = {
        "owner": OUTPUT_OWNERSHIP_OWNER,
        "project_slug": project_slug,
        "purpose": OUTPUT_OWNERSHIP_PURPOSE,
        "created_at": existing.get("created_at") or current_timestamp(),
    }
    if existing != data:
        write_json_file(ownership_path, data)


def output_ownership_status(project_export_dir: Path, project_slug: str) -> str:
    ownership_path = project_export_dir / OUTPUT_OWNERSHIP_FILENAME
    ownership = read_json_file(ownership_path)
    if not ownership:
        return "missing_ownership_metadata"
    if (
        ownership.get("owner") == OUTPUT_OWNERSHIP_OWNER
        and ownership.get("project_slug") == project_slug
        and ownership.get("purpose") == OUTPUT_OWNERSHIP_PURPOSE
    ):
        return "matched"
    return "ownership_mismatch"


def output_ownership_matches(project_export_dir: Path, project_slug: str) -> bool:
    return output_ownership_status(project_export_dir, project_slug) == "matched"


def is_under_managed_exports_root(path: Path, exports_root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(exports_root.resolve(strict=False))
    except ValueError:
        return False
    return True


def preserved_output_message(reason: str) -> str:
    messages = {
        "custom_output_directory": "自定义输出目录不会随项目历史自动删除，已保留。",
        "imported_output_directory": "导入项目的原始目录不会随项目历史自动删除，已保留。",
        "missing_ownership_metadata": "输出目录缺少系统归属标记，无法确认安全删除，已保留。",
        "ownership_mismatch": "输出目录归属标记与当前项目不匹配，已保留。",
        "outside_managed_export_root": "输出目录不在系统托管导出根目录内，已保留。",
        "unexpected_output_directory": "输出目录不符合系统托管项目目录结构，已保留。",
    }
    return messages.get(reason, "输出目录未自动删除，已保留。")


def append_preserved_output(
    preserved: List[Dict[str, str]],
    seen_paths: set[str],
    path: Path,
    reason: str,
) -> None:
    resolved = path.expanduser().resolve(strict=False)
    key = os.path.normcase(str(resolved))
    if key in seen_paths:
        return
    seen_paths.add(key)
    preserved.append(
        {
            "path": str(resolved),
            "reason": reason,
            "message": preserved_output_message(reason),
        }
    )


def project_export_dir_from_metadata(
    *,
    default_output_directory: str,
    workflow_type: str,
    project_slug: str,
    fallback_project_export_dir: Path,
) -> Path:
    default_dir = Path(default_output_directory).expanduser().resolve(strict=False)
    workflow_subdir = workflow_export_subdir(workflow_type)
    if default_dir.name == workflow_subdir and default_dir.parent.name == project_slug:
        return default_dir.parent
    if default_dir.name == project_slug:
        return default_dir
    return fallback_project_export_dir


def resolve_project_output_selection(
    *,
    default_dir: Path,
    custom_output_directory: str = "",
    create: bool = False,
) -> tuple[Path, str]:
    custom = custom_output_directory.strip()
    if custom:
        path = Path(custom).expanduser().resolve(strict=False)
        if path.exists() and not path.is_dir():
            raise ValueError("输出目录不能是文件")
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path, str(path)
    return default_dir, ""


def resolve_optional_output_selection(
    *,
    default_dir: Path,
    custom_output_directory: str = "",
    create: bool = True,
) -> tuple[Path, str]:
    custom = custom_output_directory.strip()
    if custom:
        try:
            path = Path(custom).expanduser().resolve(strict=False)
            if path.exists() and not path.is_dir():
                return default_dir, ""
            if create:
                path.mkdir(parents=True, exist_ok=True)
            elif not path.exists():
                return default_dir, ""
            return path, str(path)
        except OSError:
            return default_dir, ""
    return default_dir, ""


def current_output_dir(default_output_directory: str, custom_output_directory: str = "") -> Path:
    return Path(custom_output_directory or default_output_directory).expanduser().resolve(strict=False)


def count_files_recursive(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def ensure_not_nested_output_migration(previous_dir: Path, next_dir: Path) -> None:
    try:
        next_dir.relative_to(previous_dir)
        raise ValueError("新输出目录不能位于旧输出目录内部")
    except ValueError as exc:
        if "不能位于" in str(exc):
            raise
    try:
        previous_dir.relative_to(next_dir)
        raise ValueError("旧输出目录不能位于新输出目录内部")
    except ValueError as exc:
        if "不能位于" in str(exc):
            raise


def migrate_output_files(previous_dir: Path, next_dir: Path) -> None:
    if previous_dir == next_dir or not previous_dir.exists():
        return
    if previous_dir.exists() and not previous_dir.is_dir():
        raise ValueError("旧输出路径不是目录")
    if next_dir.exists() and not next_dir.is_dir():
        raise ValueError("新输出路径不是目录")
    ensure_not_nested_output_migration(previous_dir, next_dir)
    next_dir.mkdir(parents=True, exist_ok=True)
    for item in previous_dir.iterdir():
        target = next_dir / item.name
        if target.exists():
            raise ValueError(f"新输出目录已存在同名文件或文件夹：{item.name}")
    for item in previous_dir.iterdir():
        shutil.move(str(item), str(next_dir / item.name))
    try:
        previous_dir.rmdir()
    except OSError:
        pass


def delete_project_files(
    *,
    project_slug: str,
    project_dir: Path,
    export_dir: Path,
    managed_exports_root: Path,
    custom_output_directory: str = "",
    imported_from_path: str = "",
) -> Dict[str, Any]:
    preserved_outputs: List[Dict[str, str]] = []
    seen_preserved_paths: set[str] = set()
    result: Dict[str, Any] = {
        "project_slug": project_slug,
        "deleted_project_directory": False,
        "deleted_output_directories": [],
        "preserved_output_directories": preserved_outputs,
    }

    if custom_output_directory:
        custom_dir = Path(custom_output_directory)
        if custom_dir.exists():
            reason = "imported_output_directory" if imported_from_path else "custom_output_directory"
            append_preserved_output(preserved_outputs, seen_preserved_paths, custom_dir, reason)

    if project_dir.exists():
        shutil.rmtree(project_dir)
        result["deleted_project_directory"] = True
    if (
        export_dir.exists()
        and export_dir.name == project_slug
        and is_under_managed_exports_root(export_dir, managed_exports_root)
        and output_ownership_matches(export_dir, project_slug)
    ):
        shutil.rmtree(export_dir)
        result["deleted_output_directories"].append(str(export_dir))
    elif export_dir.exists():
        if export_dir.name != project_slug:
            reason = "unexpected_output_directory"
        elif not is_under_managed_exports_root(export_dir, managed_exports_root):
            reason = "outside_managed_export_root"
        else:
            reason = output_ownership_status(export_dir, project_slug)
        append_preserved_output(preserved_outputs, seen_preserved_paths, export_dir, reason)
    return result
