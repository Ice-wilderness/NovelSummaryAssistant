from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from logic.prompts import (
    USER_FACING_BIG_CHAR_SUBDIR,
    USER_FACING_BIG_PLOT_SUBDIR,
    USER_FACING_SMALL_CHAR_SUBDIR,
    USER_FACING_SMALL_PLOT_SUBDIR,
    USER_FACING_SUPER_CHAR_P1_SUBDIR,
    USER_FACING_SUPER_CHAR_P2_SUBDIR,
    USER_FACING_SUPER_PLOT_P1_SUBDIR,
    USER_FACING_SUPER_PLOT_P2_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P1_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P2_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P1_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P2_SUBDIR,
)
from logic.chapter_splitter import split_novel_into_chapter_files
from logic.trigger_scan.reporting import (
    REPORT_INDEX_FILENAME,
    REPORTS_DIR,
    TRIGGER_SCAN_DIR,
)
from logic.utils import (
    chinese_to_arabic,
    get_chapter_range_from_filename,
    natural_sort_key,
    normalize_summary_output_format,
    read_file_content_robustly,
)

from .file_services import safe_filename


WORKFLOW_EXPORT_SUBDIRS = {
    "novel_summary": "novel-summary",
    "article_summary": "article-summary",
    "custom_summary": "custom-summary",
    "chapter_split": "chapter-split",
}
PROJECT_METADATA_FILENAME = "project.json"
OUTPUT_OWNERSHIP_FILENAME = ".nsa_output_owner.json"
OUTPUT_OWNERSHIP_OWNER = "NovelSummaryAssistant"
OUTPUT_OWNERSHIP_PURPOSE = "managed_project_export_root"
ARTICLE_STATE_FILENAME = "article_summary_state.json"
ALLOWED_UPLOAD_SUFFIXES = {".txt"}
SUMMARY_OUTPUT_SUFFIXES = {".txt", ".md"}
MAX_UPLOAD_FILE_BYTES = 100 * 1024 * 1024
MAX_UPLOAD_BATCH_BYTES = 100 * 1024 * 1024
CHAPTER_NUMBER_PATTERN = r"[一二三四五六七八九十百千万亿零\d]+"
CHAPTER_HEADING_PATTERN = re.compile(
    rf"^\s*((第\s*{CHAPTER_NUMBER_PATTERN}\s*(?:章|节|回)).*)",
    re.MULTILINE,
)
FILENAME_RANGE_PATTERN = re.compile(
    rf"第\s*({CHAPTER_NUMBER_PATTERN})\s*章\s*[-–—~_至到]+\s*(?:第\s*)?({CHAPTER_NUMBER_PATTERN})\s*章",
    re.IGNORECASE,
)


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


def _read_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json_file(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def _count_text_files(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return len([item for item in path.glob("*.txt") if item.is_file()])


def _text_file_names(path: Path) -> set[str]:
    if not path.exists() or not path.is_dir():
        return set()
    return {item.name for item in path.glob("*.txt") if item.is_file()}


def _summary_file_paths(path: Path) -> List[Path]:
    if not path.exists() or not path.is_dir():
        return []
    return [
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in SUMMARY_OUTPUT_SUFFIXES
    ]


def _summary_file_stems(path: Path) -> set[str]:
    return {item.stem for item in _summary_file_paths(path)}


def _count_summary_files(path: Path) -> int:
    return len(_summary_file_paths(path))


def _small_summary_chapter_coverage(filename: str) -> int:
    match = re.match(r"^small_batch_(.+)_to_(.+)(?:\.(?:txt|md))?$", filename)
    if not match:
        return 1
    start, _ = get_chapter_range_from_filename(match.group(1))
    end, _ = get_chapter_range_from_filename(match.group(2))
    if start == 99999 or end == 99999 or end < start:
        return 1
    return end - start + 1


def _count_small_summary_covered_chapters(cache_dir: Path) -> int:
    plot_stems = _summary_file_stems(cache_dir / USER_FACING_SMALL_PLOT_SUBDIR)
    char_stems = _summary_file_stems(cache_dir / USER_FACING_SMALL_CHAR_SUBDIR)
    return sum(_small_summary_chapter_coverage(stem) for stem in plot_stems & char_stems)


def _chapter_span_from_filename(filename: str) -> int:
    match = FILENAME_RANGE_PATTERN.search(filename)
    if not match:
        return 1
    start = chinese_to_arabic(match.group(1))
    end = chinese_to_arabic(match.group(2))
    if start <= 0 or end <= start:
        return 1
    return end - start + 1


def _chapter_parts_from_content(content: str) -> List[str]:
    matches = list(CHAPTER_HEADING_PATTERN.finditer(content))
    if not matches:
        return []
    parts: List[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        chapter_text = content[start:end].strip()
        if chapter_text:
            parts.append(chapter_text)
    return parts


def _legacy_granularity_info(root: Path) -> Dict[str, Any]:
    grouped_files = []
    inferred_sizes: List[int] = []
    if not root.exists() or not root.is_dir():
        return {
            "requires_migration": False,
            "inferred_summary_batch_size": 10,
            "grouped_file_count": 0,
            "grouped_files": [],
        }

    for path in sorted(root.glob("*.txt"), key=lambda item: natural_sort_key(item.name)):
        if not path.is_file():
            continue
        filename_span = _chapter_span_from_filename(path.name)
        content_span = 1
        try:
            content_span = max(len(_chapter_parts_from_content(read_file_content_robustly(str(path)))), 1)
        except Exception:
            content_span = 1
        chapter_count = max(filename_span, content_span)
        if chapter_count > 1:
            inferred_sizes.append(chapter_count)
            reasons = []
            if filename_span > 1:
                reasons.append("filename_range")
            if content_span > 1:
                reasons.append("multiple_headings")
            grouped_files.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "chapter_count": chapter_count,
                    "reasons": reasons,
                }
            )

    inferred_size = max(inferred_sizes) if inferred_sizes else 10
    return {
        "requires_migration": bool(grouped_files),
        "inferred_summary_batch_size": inferred_size,
        "grouped_file_count": len(grouped_files),
        "grouped_files": grouped_files,
    }


def _count_files_recursive(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def _count_paragraph_index_files(root: Path) -> int:
    paragraph_dir = root / ".summarizer_cache" / "paragraph_index"
    if not paragraph_dir.exists() or not paragraph_dir.is_dir():
        return 0
    return len([item for item in paragraph_dir.glob("*.json") if item.is_file()])


def _scan_trigger_scan_artifacts(root: Path) -> Dict[str, int]:
    scan_dir = root / TRIGGER_SCAN_DIR
    reports_dir = scan_dir / REPORTS_DIR
    report_count = 0
    if reports_dir.exists() and reports_dir.is_dir():
        report_count = len(
            [
                item
                for item in reports_dir.glob("*.json")
                if item.is_file() and item.name != REPORT_INDEX_FILENAME
            ]
        )
        index = _read_json_file(reports_dir / REPORT_INDEX_FILENAME)
        if report_count == 0 and isinstance(index.get("items"), list):
            report_count = len(index["items"])

    return {
        "report_count": report_count,
        "paragraph_index_count": _count_paragraph_index_files(root),
    }


def _project_progress_empty(workflow_type: str) -> Dict[str, Any]:
    return {
        "workflow_type": workflow_type,
        "summary": "暂无进度",
        "percent": 0,
        "stages": [],
    }


def _status_from_progress(progress: Dict[str, Any]) -> str:
    percent = int(progress.get("percent") or 0)
    if percent >= 100:
        return "success"
    if percent > 0:
        return "partial"
    return ""


@dataclass
class UploadedFileRef:
    id: str
    project_slug: str
    original_name: str
    stored_name: str
    path: str
    size: int
    uploaded_at: float = field(default_factory=current_timestamp)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UploadedFileRef":
        return cls(
            id=str(data.get("id", "")),
            project_slug=str(data.get("project_slug", "")),
            original_name=str(data.get("original_name", "")),
            stored_name=str(data.get("stored_name", "")),
            path=str(data.get("path", "")),
            size=int(data.get("size", 0)),
            uploaded_at=float(data.get("uploaded_at", current_timestamp())),
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["missing"] = not Path(self.path).exists()
        return data


@dataclass
class ProjectMetadata:
    project_name: str
    project_slug: str
    workflow_type: str
    default_output_directory: str
    custom_output_directory: str = ""
    summary_batch_size: int = 10
    summary_output_format: str = "md"
    requires_granularity_migration: bool = False
    legacy_grouped_file_count: int = 0
    granularity_migration_backup_path: str = ""
    uploads: List[UploadedFileRef] = field(default_factory=list)
    latest_task_id: str = ""
    latest_task_status: str = ""
    imported_from_path: str = ""
    progress: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=current_timestamp)
    updated_at: float = field(default_factory=current_timestamp)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectMetadata":
        return cls(
            project_name=str(data.get("project_name", "")),
            project_slug=str(data.get("project_slug", "")),
            workflow_type=str(data.get("workflow_type", "")),
            default_output_directory=str(data.get("default_output_directory", "")),
            custom_output_directory=str(data.get("custom_output_directory", "")),
            summary_batch_size=int(data.get("summary_batch_size", 10) or 10),
            summary_output_format=normalize_summary_output_format(
                data.get("summary_output_format", "md")
            ),
            requires_granularity_migration=bool(data.get("requires_granularity_migration", False)),
            legacy_grouped_file_count=int(data.get("legacy_grouped_file_count", 0) or 0),
            granularity_migration_backup_path=str(data.get("granularity_migration_backup_path", "")),
            uploads=[UploadedFileRef.from_dict(item) for item in data.get("uploads", [])],
            latest_task_id=str(data.get("latest_task_id", "")),
            latest_task_status=str(data.get("latest_task_status", "")),
            imported_from_path=str(data.get("imported_from_path", "")),
            progress=dict(data.get("progress") or {}),
            created_at=float(data.get("created_at", current_timestamp())),
            updated_at=float(data.get("updated_at", current_timestamp())),
        )

    def to_dict(self) -> Dict[str, Any]:
        missing_uploads = [
            upload.original_name for upload in self.uploads if not Path(upload.path).exists()
        ]
        warnings = [f"缺失上传文件：{name}" for name in missing_uploads]
        if self.requires_granularity_migration:
            warnings.append(
                f"检测到 {self.legacy_grouped_file_count} 个旧版多章合并文件，需要先迁移为单章文件"
            )
        return {
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            "workflow_type": self.workflow_type,
            "default_output_directory": self.default_output_directory,
            "custom_output_directory": self.custom_output_directory,
            "summary_batch_size": self.summary_batch_size,
            "summary_output_format": self.summary_output_format,
            "requires_granularity_migration": self.requires_granularity_migration,
            "legacy_grouped_file_count": self.legacy_grouped_file_count,
            "granularity_migration_backup_path": self.granularity_migration_backup_path,
            "uploads": [upload.to_dict() for upload in self.uploads],
            "upload_count": len(self.uploads),
            "latest_task_id": self.latest_task_id,
            "latest_task_status": self.latest_task_status,
            "imported_from_path": self.imported_from_path,
            "progress": self.progress or _project_progress_empty(self.workflow_type),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "warnings": warnings,
        }


class ProjectWorkspaceService:
    def __init__(
        self,
        runtime_base_path: str | Path,
        *,
        default_export_directory: str = "",
    ) -> None:
        self.runtime_base_path = Path(runtime_base_path)
        self.default_export_directory = default_export_directory.strip()

    @property
    def workspace_root(self) -> Path:
        return self.runtime_base_path / "workspace" / "projects"

    @property
    def exports_root(self) -> Path:
        configured = self._configured_exports_root(create=False)
        return configured or self.runtime_base_path / "exports"

    @property
    def fallback_exports_root(self) -> Path:
        return self.runtime_base_path / "exports"

    def _configured_exports_root(self, *, create: bool) -> Optional[Path]:
        if not self.default_export_directory:
            return None
        try:
            path = Path(self.default_export_directory).expanduser().resolve(strict=False)
            if path.exists() and not path.is_dir():
                return None
            if create:
                path.mkdir(parents=True, exist_ok=True)
            elif not path.exists():
                return None
            return path
        except OSError:
            return None

    def effective_exports_root(self, *, create: bool = False) -> Path:
        configured = self._configured_exports_root(create=create)
        if configured is not None:
            return configured
        path = self.fallback_exports_root
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def project_dir(self, project_slug: str) -> Path:
        return self.workspace_root / project_slug

    def inputs_dir(self, project_slug: str) -> Path:
        return self.project_dir(project_slug) / "inputs"

    def metadata_path(self, project_slug: str) -> Path:
        return self.project_dir(project_slug) / PROJECT_METADATA_FILENAME

    def default_export_dir(
        self,
        project_slug: str,
        workflow_type: str = "",
        *,
        create: bool = False,
    ) -> Path:
        project_export_dir = self.effective_exports_root(create=create) / project_slug
        path = project_export_dir
        if workflow_type:
            path = path / workflow_export_subdir(workflow_type)
        if create:
            path.mkdir(parents=True, exist_ok=True)
            self._write_output_ownership(project_export_dir, project_slug)
        return path

    def _write_output_ownership(self, project_export_dir: Path, project_slug: str) -> None:
        ownership_path = project_export_dir / OUTPUT_OWNERSHIP_FILENAME
        existing = _read_json_file(ownership_path)
        data = {
            "owner": OUTPUT_OWNERSHIP_OWNER,
            "project_slug": project_slug,
            "purpose": OUTPUT_OWNERSHIP_PURPOSE,
            "created_at": existing.get("created_at") or current_timestamp(),
        }
        if existing != data:
            _write_json_file(ownership_path, data)

    def _project_export_dir_from_metadata(self, metadata: ProjectMetadata) -> Path:
        default_dir = Path(metadata.default_output_directory).expanduser().resolve(strict=False)
        workflow_subdir = workflow_export_subdir(metadata.workflow_type)
        if default_dir.name == workflow_subdir and default_dir.parent.name == metadata.project_slug:
            return default_dir.parent
        if default_dir.name == metadata.project_slug:
            return default_dir
        return self.default_export_dir(metadata.project_slug, metadata.workflow_type).parent

    def _unique_project_slug(self, base_slug: str) -> str:
        slug = safe_filename(base_slug, max_length=90).strip(" ._") or "project"
        candidate = slug
        counter = 2
        while self.metadata_path(candidate).exists():
            candidate = f"{slug}_{counter}"
            counter += 1
        return candidate

    def ensure_project(
        self,
        project_name: str,
        workflow_type: str,
        project_slug: str = "",
    ) -> ProjectMetadata:
        if project_slug:
            slug = safe_filename(project_slug, max_length=90).strip(" ._")
            if not slug:
                raise ValueError("project_slug is invalid")
            display_name = project_name.strip() or slug
        else:
            display_name, slug = sanitize_project_name(project_name)

        existing = self.load_project(slug, required=False)
        if existing:
            existing.project_name = display_name
            existing.workflow_type = workflow_type or existing.workflow_type
            existing.default_output_directory = str(
                self.default_export_dir(slug, existing.workflow_type)
            )
            existing.updated_at = current_timestamp()
            self.save_project(existing)
            return existing

        metadata = ProjectMetadata(
            project_name=display_name,
            project_slug=slug,
            workflow_type=workflow_type,
            default_output_directory=str(self.default_export_dir(slug, workflow_type)),
        )
        self.save_project(metadata)
        return metadata

    def save_project(self, metadata: ProjectMetadata) -> None:
        metadata.updated_at = current_timestamp()
        metadata.default_output_directory = str(
            self.default_export_dir(metadata.project_slug, metadata.workflow_type)
        )
        self.refresh_granularity_metadata(metadata)
        metadata.progress = self.scan_project_progress(metadata)
        path = self.metadata_path(metadata.project_slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata.to_dict(), handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)

    def refresh_granularity_metadata(self, metadata: ProjectMetadata) -> Dict[str, Any]:
        if metadata.workflow_type not in {"novel_summary", "chapter_split"}:
            metadata.requires_granularity_migration = False
            metadata.legacy_grouped_file_count = 0
            return {
                "requires_migration": False,
                "inferred_summary_batch_size": metadata.summary_batch_size,
                "grouped_file_count": 0,
                "grouped_files": [],
            }

        root = Path(metadata.custom_output_directory or metadata.default_output_directory).expanduser().resolve(strict=False)
        info = _legacy_granularity_info(root)
        metadata.requires_granularity_migration = bool(info["requires_migration"])
        metadata.legacy_grouped_file_count = int(info["grouped_file_count"])
        if metadata.requires_granularity_migration:
            metadata.summary_batch_size = int(info["inferred_summary_batch_size"])
        elif metadata.summary_batch_size <= 0:
            metadata.summary_batch_size = 10
        return info

    def load_project(
        self,
        project_slug: str,
        *,
        required: bool = True,
    ) -> Optional[ProjectMetadata]:
        path = self.metadata_path(project_slug)
        if not path.exists():
            if required:
                raise ValueError(f"项目不存在：{project_slug}")
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                return ProjectMetadata.from_dict(json.load(handle))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"项目元数据不可用：{project_slug}") from exc

    def list_projects(self, workflow_type: str = "") -> List[ProjectMetadata]:
        if not self.workspace_root.exists():
            return []
        projects: List[ProjectMetadata] = []
        for metadata_file in self.workspace_root.glob(f"*/{PROJECT_METADATA_FILENAME}"):
            try:
                metadata = ProjectMetadata.from_dict(
                    json.loads(metadata_file.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if workflow_type and metadata.workflow_type != workflow_type:
                continue
            metadata.progress = self.scan_project_progress(metadata)
            projects.append(metadata)
        return sorted(projects, key=lambda item: item.updated_at, reverse=True)

    def rename_project(self, project_slug: str, project_name: str) -> ProjectMetadata:
        display_name = project_name.strip()
        if not display_name:
            raise ValueError("项目名称不能为空")
        metadata = self.load_project(project_slug)
        metadata.project_name = display_name
        self.save_project(metadata)
        return metadata

    def import_project_directory(
        self,
        *,
        source_directory: str | Path,
        workflow_type: str,
        project_name: str = "",
    ) -> ProjectMetadata:
        source_dir = Path(source_directory).expanduser().resolve(strict=True)
        if not source_dir.is_dir():
            raise ValueError("导入路径必须是目录")
        display_name, base_slug = sanitize_project_name(project_name or source_dir.name)
        slug = self._unique_project_slug(base_slug)
        metadata = ProjectMetadata(
            project_name=display_name,
            project_slug=slug,
            workflow_type=workflow_type,
            default_output_directory=str(self.default_export_dir(slug, workflow_type)),
            custom_output_directory=str(source_dir),
            imported_from_path=str(source_dir),
        )

        inputs_dir = self.inputs_dir(slug)
        inputs_dir.mkdir(parents=True, exist_ok=True)
        uploads: List[UploadedFileRef] = []
        for source_file in sorted(source_dir.glob("*.txt"), key=lambda item: item.name):
            if not source_file.is_file():
                continue
            stored_name = self._unique_stored_name(inputs_dir, source_file.name)
            input_target = inputs_dir / stored_name
            shutil.copyfile(source_file, input_target)
            uploads.append(
                UploadedFileRef(
                    id=uuid.uuid4().hex,
                    project_slug=slug,
                    original_name=source_file.name,
                    stored_name=stored_name,
                    path=str(input_target),
                    size=input_target.stat().st_size,
                )
            )

        if not uploads:
            raise ValueError("导入目录中没有可用的 .txt 文件")

        legacy_cache_dir = self._find_legacy_cache_dir(source_dir, workflow_type)
        if legacy_cache_dir and legacy_cache_dir != source_dir / ".summarizer_cache":
            target_cache = source_dir / ".summarizer_cache"
            if target_cache.exists():
                shutil.rmtree(target_cache)
            shutil.copytree(legacy_cache_dir, target_cache)

        metadata.uploads = uploads
        metadata.progress = self.scan_project_progress(metadata)
        metadata.latest_task_status = _status_from_progress(metadata.progress)
        self.save_project(metadata)
        return metadata

    def upload_text_files(
        self,
        *,
        project_name: str,
        workflow_type: str,
        files: Iterable[Dict[str, Any]],
        project_slug: str = "",
    ) -> ProjectMetadata:
        incoming = list(files)
        if not incoming:
            raise ValueError("请至少选择一个文本文件")

        metadata = self.ensure_project(project_name, workflow_type, project_slug)
        inputs_dir = self.inputs_dir(metadata.project_slug)
        inputs_dir.mkdir(parents=True, exist_ok=True)

        batch_size = 0
        uploads: List[UploadedFileRef] = []
        for item in incoming:
            original_name = str(item.get("name", "")).strip()
            content = item.get("content")
            if not original_name:
                raise ValueError("上传文件缺少文件名")
            if not isinstance(content, str):
                raise ValueError(f"{original_name} 缺少文本内容")
            if Path(original_name).suffix.lower() not in ALLOWED_UPLOAD_SUFFIXES:
                raise ValueError(f"{original_name} 不是受支持的文本文件")

            encoded = content.encode("utf-8")
            size = len(encoded)
            if size > MAX_UPLOAD_FILE_BYTES:
                raise ValueError(f"{original_name} 超过单文件大小限制")
            batch_size += size
            if batch_size > MAX_UPLOAD_BATCH_BYTES:
                raise ValueError("本次上传超过总大小限制")

            stored_name = self._unique_stored_name(inputs_dir, original_name)
            target = inputs_dir / stored_name
            target.write_bytes(encoded)
            uploads.append(
                UploadedFileRef(
                    id=uuid.uuid4().hex,
                    project_slug=metadata.project_slug,
                    original_name=original_name,
                    stored_name=stored_name,
                    path=str(target),
                    size=size,
                )
            )

        metadata.uploads.extend(uploads)
        metadata.default_output_directory = str(
            self.default_export_dir(metadata.project_slug, metadata.workflow_type)
        )
        self.save_project(metadata)
        return metadata

    def resolve_upload_refs(
        self,
        project_slug: str,
        upload_ids: Iterable[str],
    ) -> List[UploadedFileRef]:
        requested = [str(upload_id) for upload_id in upload_ids if str(upload_id).strip()]
        if not requested:
            raise ValueError("uploaded_file_ids is required")
        metadata = self.load_project(project_slug)
        upload_map = {upload.id: upload for upload in metadata.uploads}
        resolved: List[UploadedFileRef] = []
        for upload_id in requested:
            upload = upload_map.get(upload_id)
            if upload is None:
                raise ValueError(f"未知上传文件引用：{upload_id}")
            if not Path(upload.path).exists():
                raise ValueError(f"上传文件已缺失：{upload.original_name}")
            resolved.append(upload)
        return resolved

    def clear_project_uploads(self, project_slug: str) -> ProjectMetadata:
        metadata = self.load_project(project_slug)
        for upload in metadata.uploads:
            try:
                Path(upload.path).unlink(missing_ok=True)
            except OSError:
                continue
        inputs_dir = self.inputs_dir(project_slug)
        if inputs_dir.exists():
            for item in inputs_dir.iterdir():
                if item.is_file():
                    try:
                        item.unlink()
                    except OSError:
                        continue
        metadata.uploads = []
        self.save_project(metadata)
        return metadata

    def _resolve_project_output_selection(
        self,
        metadata: ProjectMetadata,
        custom_output_directory: str = "",
        *,
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
        return self.default_export_dir(metadata.project_slug, metadata.workflow_type, create=create), ""

    def _current_output_dir(self, metadata: ProjectMetadata) -> Path:
        return Path(metadata.custom_output_directory or metadata.default_output_directory).expanduser().resolve(strict=False)

    def output_migration_info(
        self,
        project_slug: str,
        *,
        custom_output_directory: str = "",
    ) -> Dict[str, Any]:
        metadata = self.load_project(project_slug)
        previous_dir = self._current_output_dir(metadata)
        next_dir, effective_custom = self._resolve_project_output_selection(
            metadata,
            custom_output_directory,
            create=False,
        )
        file_count = _count_files_recursive(previous_dir)
        requires_migration = previous_dir != next_dir and file_count > 0
        return {
            "requires_migration": requires_migration,
            "file_count": file_count,
            "previous_output_directory": str(previous_dir),
            "new_output_directory": str(next_dir),
            "custom_output_directory": effective_custom,
        }

    def _ensure_not_nested_output_migration(self, previous_dir: Path, next_dir: Path) -> None:
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

    def _migrate_output_files(self, previous_dir: Path, next_dir: Path) -> None:
        if previous_dir == next_dir or not previous_dir.exists():
            return
        if previous_dir.exists() and not previous_dir.is_dir():
            raise ValueError("旧输出路径不是目录")
        if next_dir.exists() and not next_dir.is_dir():
            raise ValueError("新输出路径不是目录")
        self._ensure_not_nested_output_migration(previous_dir, next_dir)
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

    def save_project_draft(
        self,
        project_slug: str,
        *,
        project_name: str = "",
        uploaded_file_ids: Optional[Iterable[str]] = None,
        custom_output_directory: str = "",
        migrate_existing_output: bool = False,
        summary_output_format: str = "",
        summary_batch_size: int = 0,
    ) -> ProjectMetadata:
        metadata = self.load_project(project_slug)
        if project_name.strip():
            metadata.project_name = project_name.strip()
        if summary_output_format:
            metadata.summary_output_format = normalize_summary_output_format(summary_output_format)
        if summary_batch_size > 0:
            metadata.summary_batch_size = summary_batch_size
        if uploaded_file_ids is not None:
            requested_ids = [str(upload_id) for upload_id in uploaded_file_ids]
            upload_map = {upload.id: upload for upload in metadata.uploads}
            unknown_ids = [upload_id for upload_id in requested_ids if upload_id not in upload_map]
            if unknown_ids:
                raise ValueError(f"未知上传文件引用：{unknown_ids[0]}")
            removed_uploads = [upload for upload in metadata.uploads if upload.id not in requested_ids]
            for upload in removed_uploads:
                try:
                    Path(upload.path).unlink(missing_ok=True)
                except OSError:
                    continue
            metadata.uploads = [upload_map[upload_id] for upload_id in requested_ids]

        previous_dir = self._current_output_dir(metadata)
        next_dir, effective_custom = self._resolve_project_output_selection(
            metadata,
            custom_output_directory,
            create=True,
        )
        if migrate_existing_output and previous_dir != next_dir and _count_files_recursive(previous_dir) > 0:
            self._migrate_output_files(previous_dir, next_dir)
        metadata.custom_output_directory = effective_custom
        self.save_project(metadata)
        return metadata

    def check_chapter_granularity_migration(self, project_slug: str) -> Dict[str, Any]:
        metadata = self.load_project(project_slug)
        info = self.refresh_granularity_metadata(metadata)
        self.save_project(metadata)
        return {
            **info,
            "summary_batch_size": metadata.summary_batch_size,
            "project_slug": metadata.project_slug,
        }

    def _replace_uploads_from_directory(self, metadata: ProjectMetadata, source_dir: Path) -> None:
        inputs_dir = self.inputs_dir(metadata.project_slug)
        if inputs_dir.exists():
            shutil.rmtree(inputs_dir)
        inputs_dir.mkdir(parents=True, exist_ok=True)

        uploads: List[UploadedFileRef] = []
        for source_file in sorted(source_dir.glob("*.txt"), key=lambda item: natural_sort_key(item.name)):
            if not source_file.is_file():
                continue
            stored_name = self._unique_stored_name(inputs_dir, source_file.name)
            input_target = inputs_dir / stored_name
            shutil.copyfile(source_file, input_target)
            uploads.append(
                UploadedFileRef(
                    id=uuid.uuid4().hex,
                    project_slug=metadata.project_slug,
                    original_name=source_file.name,
                    stored_name=stored_name,
                    path=str(input_target),
                    size=input_target.stat().st_size,
                )
            )
        metadata.uploads = uploads

    def _create_granularity_backup(self, root: Path) -> Path:
        backup_dir = (
            root
            / ".granularity_migration_backup"
            / f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )
        backup_dir.mkdir(parents=True, exist_ok=True)
        for source_file in root.glob("*.txt"):
            if source_file.is_file():
                shutil.copyfile(source_file, backup_dir / source_file.name)
        cache_dir = root / ".summarizer_cache"
        if cache_dir.exists() and cache_dir.is_dir():
            shutil.copytree(cache_dir, backup_dir / ".summarizer_cache")
        return backup_dir

    def _write_migrated_chapter(self, output_dir: Path, chapter_index: int, content: str) -> None:
        target = output_dir / f"第{chapter_index:03d}章.txt"
        target.write_text(content.strip(), encoding="utf-8")

    def _build_migration_from_grouped_files(
        self,
        root: Path,
        temp_dir: Path,
        info: Dict[str, Any],
    ) -> int:
        grouped_names = {str(item["name"]) for item in info.get("grouped_files", [])}
        chapter_index = 1
        for source_file in sorted(root.glob("*.txt"), key=lambda item: natural_sort_key(item.name)):
            if not source_file.is_file():
                continue
            content = read_file_content_robustly(str(source_file))
            chapter_parts = _chapter_parts_from_content(content)
            if source_file.name in grouped_names and len(chapter_parts) <= 1:
                raise ValueError(f"无法从合并文件解析多个章节：{source_file.name}")
            parts = chapter_parts or [content]
            for chapter_content in parts:
                if not chapter_content.strip():
                    continue
                self._write_migrated_chapter(temp_dir, chapter_index, chapter_content)
                chapter_index += 1
        return chapter_index - 1

    def _build_migration_from_original_txt(
        self,
        source_txt_file_path: str,
        temp_dir: Path,
    ) -> int:
        source_path = Path(source_txt_file_path).expanduser().resolve(strict=True)
        if not source_path.is_file():
            raise ValueError("原始 TXT 路径必须是文件")
        success, count = split_novel_into_chapter_files(
            str(source_path),
            str(temp_dir),
            handle_volumes=True,
            log_callback=lambda *args, **kwargs: None,
            mode="default",
        )
        if not success or count <= 0:
            raise ValueError("无法从原始 TXT 重新拆分章节")
        return count

    def _apply_granularity_migration_output(
        self,
        root: Path,
        temp_dir: Path,
    ) -> None:
        for source_file in root.glob("*.txt"):
            if source_file.is_file():
                source_file.unlink()
        cache_dir = root / ".summarizer_cache"
        if cache_dir.exists() and cache_dir.is_dir():
            shutil.rmtree(cache_dir)
        for migrated_file in sorted(temp_dir.glob("*.txt"), key=lambda item: natural_sort_key(item.name)):
            shutil.move(str(migrated_file), str(root / migrated_file.name))

    def migrate_chapter_granularity(
        self,
        project_slug: str,
        *,
        source_txt_file_path: str = "",
    ) -> tuple[ProjectMetadata, Dict[str, Any]]:
        metadata = self.load_project(project_slug)
        if metadata.workflow_type not in {"novel_summary", "chapter_split"}:
            raise ValueError("只有小说总结或章节分割项目需要章节粒度迁移")

        root = Path(metadata.custom_output_directory or metadata.default_output_directory).expanduser().resolve(strict=False)
        if not root.exists() or not root.is_dir():
            raise ValueError("项目输出目录不存在，无法迁移")

        info = self.refresh_granularity_metadata(metadata)
        if not info["requires_migration"] and not source_txt_file_path.strip():
            self.save_project(metadata)
            return metadata, {
                **info,
                "migrated": False,
                "generated_file_count": _count_text_files(root),
                "backup_path": metadata.granularity_migration_backup_path,
                "summary_batch_size": metadata.summary_batch_size,
            }

        inferred_summary_batch_size = metadata.summary_batch_size
        temp_dir = root / f".granularity_migration_tmp_{uuid.uuid4().hex}"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            if source_txt_file_path.strip():
                generated_count = self._build_migration_from_original_txt(source_txt_file_path, temp_dir)
            else:
                generated_count = self._build_migration_from_grouped_files(root, temp_dir, info)
            if generated_count <= 0:
                raise ValueError("迁移没有生成任何章节文件")
            backup_dir = self._create_granularity_backup(root)
            self._apply_granularity_migration_output(root, temp_dir)
        except Exception as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise ValueError(str(exc)) from exc
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        metadata.summary_batch_size = max(int(inferred_summary_batch_size or 10), 1)
        metadata.requires_granularity_migration = False
        metadata.legacy_grouped_file_count = 0
        metadata.granularity_migration_backup_path = str(backup_dir)
        self._replace_uploads_from_directory(metadata, root)
        self.save_project(metadata)
        return metadata, {
            "requires_migration": False,
            "migrated": True,
            "generated_file_count": generated_count,
            "backup_path": str(backup_dir),
            "summary_batch_size": metadata.summary_batch_size,
        }

    def split_and_ingest_source_file(
        self,
        project_slug: str,
        *,
        source_file_path: str,
        mode: str = "default",
        custom_pattern: str = "",
        title_list: list | None = None,
        handle_volumes: bool = True,
        pattern_config=None,
        log_callback=None,
    ) -> ProjectMetadata:
        """将源文件分割后直接纳入项目 inputs，替换现有 uploads 列表。

        用于小说总结入口的"上传源文件 → 分割 → 自动导入"流程。
        """
        metadata = self.load_project(project_slug)
        if log_callback is None:
            log_callback = lambda *args, **kwargs: None

        source_path = Path(source_file_path).expanduser().resolve(strict=True)
        if not source_path.is_file():
            raise ValueError("源文件路径必须是文件")

        # 在 inputs 目录中创建临时子目录用于分割输出
        inputs_dir = self.inputs_dir(project_slug)
        if inputs_dir.exists():
            # 清空旧的 inputs
            for item in inputs_dir.iterdir():
                if item.is_file():
                    item.unlink()
        inputs_dir.mkdir(parents=True, exist_ok=True)

        success, count = split_novel_into_chapter_files(
            str(source_path),
            str(inputs_dir),
            handle_volumes=handle_volumes,
            log_callback=log_callback,
            mode=mode,
            custom_pattern=custom_pattern,
            title_list=title_list or [],
            pattern_config=pattern_config,
        )
        if not success or count <= 0:
            raise ValueError("源文件分割失败，未能生成章节文件")

        # 将生成的章节文件注册为 uploads
        uploads: list = []
        for chapter_file in sorted(inputs_dir.glob("*.txt"), key=lambda item: natural_sort_key(item.name)):
            uploads.append(
                UploadedFileRef(
                    id=uuid.uuid4().hex,
                    project_slug=project_slug,
                    original_name=chapter_file.name,
                    stored_name=chapter_file.name,
                    path=str(chapter_file),
                    size=chapter_file.stat().st_size,
                )
            )

        metadata.uploads = uploads
        metadata.requires_granularity_migration = False
        metadata.legacy_grouped_file_count = 0
        self.save_project(metadata)
        return metadata

    def delete_project(self, project_slug: str) -> None:
        metadata = self.load_project(project_slug)
        project_dir = self.project_dir(project_slug)
        export_dir = self._project_export_dir_from_metadata(metadata)
        if project_dir.exists():
            shutil.rmtree(project_dir)
        if export_dir.exists() and export_dir.name == project_slug:
            shutil.rmtree(export_dir)

    def resolve_output_dir(
        self,
        *,
        project_slug: str,
        workflow_type: str,
        custom_output_directory: str = "",
        create: bool = True,
    ) -> Path:
        output_dir, _ = self.resolve_output_selection(
            project_slug=project_slug,
            workflow_type=workflow_type,
            custom_output_directory=custom_output_directory,
            create=create,
        )
        return output_dir

    def resolve_output_selection(
        self,
        *,
        project_slug: str,
        workflow_type: str,
        custom_output_directory: str = "",
        create: bool = True,
    ) -> tuple[Path, str]:
        default_dir = self.default_export_dir(project_slug, workflow_type, create=create)
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

    def prepare_copied_inputs(
        self,
        *,
        output_dir: Path,
        uploads: Iterable[UploadedFileRef],
    ) -> List[str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        copied_names: List[str] = []
        for upload in uploads:
            target = output_dir / upload.stored_name
            shutil.copyfile(upload.path, target)
            copied_names.append(upload.stored_name)
        return copied_names

    def update_project_output(
        self,
        project_slug: str,
        *,
        project_name: str = "",
        custom_output_directory: str = "",
        latest_task_id: str = "",
        latest_task_status: str = "",
        summary_output_format: str = "",
    ) -> ProjectMetadata:
        metadata = self.load_project(project_slug)
        if project_name.strip():
            metadata.project_name = project_name.strip()
        if summary_output_format:
            metadata.summary_output_format = normalize_summary_output_format(summary_output_format)
        metadata.custom_output_directory = custom_output_directory
        if latest_task_id:
            metadata.latest_task_id = latest_task_id
        if latest_task_status:
            metadata.latest_task_status = latest_task_status
        self.save_project(metadata)
        return metadata

    def scan_project_progress(self, metadata: ProjectMetadata) -> Dict[str, Any]:
        root = Path(metadata.custom_output_directory or metadata.default_output_directory)
        if metadata.workflow_type == "novel_summary":
            return self._scan_novel_progress(root)
        if metadata.workflow_type == "article_summary":
            return self._scan_article_progress(root)
        if metadata.workflow_type == "chapter_split":
            return self._scan_splitter_progress(root)
        if metadata.latest_task_status:
            return {
                "workflow_type": metadata.workflow_type,
                "summary": f"最近任务：{metadata.latest_task_status}",
                "percent": 100 if metadata.latest_task_status == "success" else 0,
                "stages": [
                    {
                        "label": "最近任务",
                        "completed": 1 if metadata.latest_task_status == "success" else 0,
                        "total": 1,
                        "status": metadata.latest_task_status,
                    }
                ],
            }
        return _project_progress_empty(metadata.workflow_type)

    def open_directory(self, path: str | Path, *, create: bool = False) -> None:
        directory = Path(path).expanduser().resolve(strict=False)
        if directory.exists() and not directory.is_dir():
            raise ValueError("路径不是目录")
        if create:
            directory.mkdir(parents=True, exist_ok=True)
        if not directory.exists():
            raise ValueError("目录不存在")
        _open_directory_with_os(directory)

    def _find_legacy_cache_dir(self, source_dir: Path, workflow_type: str) -> Optional[Path]:
        direct_cache = source_dir / ".summarizer_cache"
        if direct_cache.exists() and direct_cache.is_dir():
            return direct_cache
        if workflow_type == "article_summary":
            for state_path in source_dir.glob(f"*/.summarizer_cache/{ARTICLE_STATE_FILENAME}"):
                return state_path.parent
        return None

    def _scan_novel_progress(self, root: Path) -> Dict[str, Any]:
        total_chapters = _count_text_files(root)
        cache_dir = root / ".summarizer_cache"
        small_completed = min(_count_small_summary_covered_chapters(cache_dir), total_chapters)
        big_plot = _count_summary_files(cache_dir / USER_FACING_BIG_PLOT_SUBDIR)
        big_char = _count_summary_files(cache_dir / USER_FACING_BIG_CHAR_SUBDIR)
        super_completed = sum(
            _count_summary_files(cache_dir / subdir)
            for subdir in [
                USER_FACING_SUPER_PLOT_P1_SUBDIR,
                USER_FACING_SUPER_PLOT_P2_SUBDIR,
                USER_FACING_SUPER_CHAR_P1_SUBDIR,
                USER_FACING_SUPER_CHAR_P2_SUBDIR,
            ]
        )
        ultimate_completed = min(
            4,
            sum(
                _count_summary_files(cache_dir / subdir)
                for subdir in [
                    USER_FACING_ULTIMATE_PLOT_P1_SUBDIR,
                    USER_FACING_ULTIMATE_PLOT_P2_SUBDIR,
                    USER_FACING_ULTIMATE_CHAR_P1_SUBDIR,
                    USER_FACING_ULTIMATE_CHAR_P2_SUBDIR,
                ]
            ),
        )
        trigger_artifacts = _scan_trigger_scan_artifacts(root)
        stages = [
            {"label": "小总结", "completed": small_completed, "total": total_chapters},
            {"label": "大总结-剧情", "completed": big_plot, "total": None},
            {"label": "大总结-角色", "completed": big_char, "total": None},
            {"label": "超级总结", "completed": super_completed, "total": None},
            {"label": "终极总结", "completed": ultimate_completed, "total": 4},
            {"label": "雷点报告", "completed": trigger_artifacts["report_count"], "total": None},
            {"label": "段落缓存", "completed": trigger_artifacts["paragraph_index_count"], "total": None},
        ]
        percent = 0
        if total_chapters > 0:
            percent = min(95, int((small_completed / total_chapters) * 35))
        if trigger_artifacts["report_count"] and percent == 0:
            percent = 10
        if ultimate_completed >= 4:
            percent = 100
        elif ultimate_completed:
            percent = max(percent, 85)
        elif super_completed:
            percent = max(percent, 70)
        elif big_plot or big_char:
            percent = max(percent, 50)
        summary = f"小总结 {small_completed}/{total_chapters}"
        if ultimate_completed >= 4:
            summary = "终极总结已完成"
        elif super_completed:
            summary = f"超级总结已完成 {super_completed} 项"
        elif big_plot or big_char:
            summary = f"大总结已完成 剧情 {big_plot} / 角色 {big_char}"
        elif trigger_artifacts["report_count"]:
            summary = f"雷点报告 {trigger_artifacts['report_count']} 份"
        return {
            "workflow_type": "novel_summary",
            "summary": summary,
            "percent": percent,
            "stages": stages,
        }

    def _scan_article_progress(self, root: Path) -> Dict[str, Any]:
        total_files = _count_text_files(root)
        state = _read_json_file(root / ".summarizer_cache" / ARTICLE_STATE_FILENAME)
        processed_sections = state.get("processed_sections", [])
        section_completed = len(processed_sections) if isinstance(processed_sections, list) else 0
        final_completed = bool(state.get("final_summary_complete"))
        percent = 0
        if total_files > 0:
            percent = min(70, int((section_completed / total_files) * 70))
        if final_completed:
            percent = 100
        return {
            "workflow_type": "article_summary",
            "summary": "最终总结已完成" if final_completed else f"段落总结 {section_completed}/{total_files}",
            "percent": percent,
            "stages": [
                {"label": "段落总结", "completed": section_completed, "total": total_files},
                {"label": "最终总结", "completed": 1 if final_completed else 0, "total": 1},
            ],
        }

    def _scan_splitter_progress(self, root: Path) -> Dict[str, Any]:
        generated_count = _count_text_files(root)
        return {
            "workflow_type": "chapter_split",
            "summary": f"已生成 {generated_count} 个 TXT 文件" if generated_count else "暂无生成文件",
            "percent": 100 if generated_count else 0,
            "stages": [
                {"label": "生成文件", "completed": generated_count, "total": None},
            ],
        }

    def _unique_stored_name(self, inputs_dir: Path, original_name: str) -> str:
        safe_name = safe_filename(Path(original_name).name, max_length=150)
        if not safe_name:
            safe_name = f"upload-{uuid.uuid4().hex}.txt"
        candidate = safe_name
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        counter = 2
        while (inputs_dir / candidate).exists():
            candidate = f"{stem}_{counter}{suffix}"
            counter += 1
        return candidate


def _open_directory_with_os(directory: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(directory))  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(directory)])
        return
    subprocess.Popen(["xdg-open", str(directory)])
