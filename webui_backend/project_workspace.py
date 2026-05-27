from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from logic.chapter_splitter import split_novel_into_chapter_files
from logic.utils import (
    natural_sort_key,
    normalize_summary_output_format,
)

from .file_services import safe_filename
from .workspace_services.low_state import (
    WORKFLOW_EXPORT_SUBDIRS,
    current_timestamp,
    sanitize_project_name,
    workflow_export_subdir,
)
from .workspace_services.outputs import (
    OUTPUT_OWNERSHIP_FILENAME,
    OUTPUT_OWNERSHIP_OWNER,
    OUTPUT_OWNERSHIP_PURPOSE,
    append_preserved_output,
    count_files_recursive as _count_files_recursive,
    current_output_dir,
    delete_project_files,
    ensure_not_nested_output_migration,
    is_under_managed_exports_root,
    migrate_output_files,
    output_ownership_matches,
    output_ownership_status,
    preserved_output_message,
    project_export_dir_from_metadata,
    resolve_optional_output_selection,
    resolve_project_output_selection,
    write_output_ownership,
)
from .workspace_services.progress import (
    find_legacy_cache_dir,
    granularity_migration_disabled_info as _granularity_migration_disabled_info,
    project_progress_empty as _project_progress_empty,
    scan_article_progress,
    scan_novel_progress,
    scan_project_progress as scan_workspace_progress,
    scan_splitter_progress,
    status_from_progress as _status_from_progress,
)
from .workspace_services.uploads import (
    MAX_UPLOAD_BATCH_BYTES,
    MAX_UPLOAD_FILE_BYTES,
    UploadedFileRef,
    prepare_copied_inputs as prepare_upload_inputs,
    refs_for_existing_files,
    remove_upload_files,
    resolve_upload_refs as resolve_stored_upload_refs,
    select_upload_refs,
    store_text_uploads,
    uploaded_ref_for_file,
    unique_stored_name,
)
from .workspace_services.local_open import (
    open_directory as open_workspace_directory,
    open_directory_with_os,
)


PROJECT_METADATA_FILENAME = "project.json"


@dataclass
class ProjectMetadata:
    project_name: str
    project_slug: str
    workflow_type: str
    default_output_directory: str
    custom_output_directory: str = ""
    summary_batch_size: int = 10
    summary_output_format: str = "md"
    use_fine_grained_flow: bool = False
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
            use_fine_grained_flow=bool(data.get("use_fine_grained_flow", False)),
            requires_granularity_migration=False,
            legacy_grouped_file_count=0,
            granularity_migration_backup_path="",
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
        return {
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            "workflow_type": self.workflow_type,
            "default_output_directory": self.default_output_directory,
            "custom_output_directory": self.custom_output_directory,
            "summary_batch_size": self.summary_batch_size,
            "summary_output_format": self.summary_output_format,
            "use_fine_grained_flow": self.use_fine_grained_flow,
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
        write_output_ownership(project_export_dir, project_slug)

    def _output_ownership_matches(self, project_export_dir: Path, project_slug: str) -> bool:
        return output_ownership_matches(project_export_dir, project_slug)

    def _output_ownership_status(self, project_export_dir: Path, project_slug: str) -> str:
        return output_ownership_status(project_export_dir, project_slug)

    def _is_under_managed_exports_root(self, path: Path) -> bool:
        return is_under_managed_exports_root(path, self.effective_exports_root(create=False))

    def _preserved_output_message(self, reason: str) -> str:
        return preserved_output_message(reason)

    def _append_preserved_output(
        self,
        preserved: List[Dict[str, str]],
        seen_paths: set[str],
        path: Path,
        reason: str,
    ) -> None:
        append_preserved_output(preserved, seen_paths, path, reason)

    def _project_export_dir_from_metadata(self, metadata: ProjectMetadata) -> Path:
        return project_export_dir_from_metadata(
            default_output_directory=metadata.default_output_directory,
            workflow_type=metadata.workflow_type,
            project_slug=metadata.project_slug,
            fallback_project_export_dir=self.default_export_dir(
                metadata.project_slug,
                metadata.workflow_type,
            ).parent,
        )

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
        metadata.requires_granularity_migration = False
        metadata.legacy_grouped_file_count = 0
        metadata.granularity_migration_backup_path = ""
        if metadata.summary_batch_size <= 0:
            metadata.summary_batch_size = 10
        return _granularity_migration_disabled_info(metadata.summary_batch_size)

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
            stored_name = unique_stored_name(inputs_dir, source_file.name)
            input_target = inputs_dir / stored_name
            shutil.copyfile(source_file, input_target)
            uploads.append(
                uploaded_ref_for_file(
                    project_slug=slug,
                    original_name=source_file.name,
                    stored_name=stored_name,
                    path=input_target,
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
        metadata = self.ensure_project(project_name, workflow_type, project_slug)
        inputs_dir = self.inputs_dir(metadata.project_slug)
        uploads = store_text_uploads(
            project_slug=metadata.project_slug,
            inputs_dir=inputs_dir,
            files=files,
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
        metadata = self.load_project(project_slug)
        return resolve_stored_upload_refs(uploads=metadata.uploads, upload_ids=upload_ids)

    def clear_project_uploads(self, project_slug: str) -> ProjectMetadata:
        metadata = self.load_project(project_slug)
        remove_upload_files(metadata.uploads)
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
        return resolve_project_output_selection(
            default_dir=self.default_export_dir(
                metadata.project_slug,
                metadata.workflow_type,
                create=create,
            ),
            custom_output_directory=custom_output_directory,
            create=create,
        )

    def _current_output_dir(self, metadata: ProjectMetadata) -> Path:
        return current_output_dir(
            metadata.default_output_directory,
            metadata.custom_output_directory,
        )

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
        ensure_not_nested_output_migration(previous_dir, next_dir)

    def _migrate_output_files(self, previous_dir: Path, next_dir: Path) -> None:
        migrate_output_files(previous_dir, next_dir)

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
        use_fine_grained_flow: Optional[bool] = None,
    ) -> ProjectMetadata:
        metadata = self.load_project(project_slug)
        if project_name.strip():
            metadata.project_name = project_name.strip()
        if summary_output_format:
            metadata.summary_output_format = normalize_summary_output_format(summary_output_format)
        if summary_batch_size > 0:
            metadata.summary_batch_size = summary_batch_size
        if use_fine_grained_flow is not None:
            metadata.use_fine_grained_flow = bool(use_fine_grained_flow)
        if uploaded_file_ids is not None:
            selected_uploads, removed_uploads = select_upload_refs(
                uploads=metadata.uploads,
                upload_ids=uploaded_file_ids,
            )
            remove_upload_files(removed_uploads)
            metadata.uploads = selected_uploads

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

        inputs_dir = self.inputs_dir(project_slug)
        inputs_dir.parent.mkdir(parents=True, exist_ok=True)
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"{project_slug}_split_", dir=str(inputs_dir.parent)))

        try:
            success, count = split_novel_into_chapter_files(
                str(source_path),
                str(tmp_dir),
                handle_volumes=handle_volumes,
                log_callback=log_callback,
                mode=mode,
                custom_pattern=custom_pattern,
                title_list=title_list or [],
                pattern_config=pattern_config,
                raise_on_error=True,
            )
            if not success or count <= 0:
                raise ValueError("源文件分割失败，未能生成章节文件")

            if inputs_dir.exists():
                for item in inputs_dir.iterdir():
                    if item.is_file():
                        item.unlink()
            inputs_dir.mkdir(parents=True, exist_ok=True)
            for chapter_file in sorted(tmp_dir.glob("*.txt"), key=lambda item: natural_sort_key(item.name)):
                shutil.move(str(chapter_file), str(inputs_dir / chapter_file.name))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        # 将生成的章节文件注册为 uploads
        chapter_files = sorted(inputs_dir.glob("*.txt"), key=lambda item: natural_sort_key(item.name))

        metadata.uploads = refs_for_existing_files(project_slug=project_slug, files=chapter_files)
        metadata.requires_granularity_migration = False
        metadata.legacy_grouped_file_count = 0
        self.save_project(metadata)
        return metadata

    def delete_project(self, project_slug: str) -> Dict[str, Any]:
        metadata = self.load_project(project_slug)
        return delete_project_files(
            project_slug=project_slug,
            project_dir=self.project_dir(project_slug),
            export_dir=self._project_export_dir_from_metadata(metadata),
            managed_exports_root=self.effective_exports_root(create=False),
            custom_output_directory=metadata.custom_output_directory,
            imported_from_path=metadata.imported_from_path,
        )

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
        return resolve_optional_output_selection(
            default_dir=default_dir,
            custom_output_directory=custom_output_directory,
            create=create,
        )

    def prepare_copied_inputs(
        self,
        *,
        output_dir: Path,
        uploads: Iterable[UploadedFileRef],
    ) -> List[str]:
        return prepare_upload_inputs(output_dir, uploads)

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
        return scan_workspace_progress(
            metadata.workflow_type,
            metadata.custom_output_directory or metadata.default_output_directory,
            metadata.latest_task_status,
        )

    def open_directory(self, path: str | Path, *, create: bool = False) -> None:
        open_workspace_directory(path, create=create, opener=_open_directory_with_os)

    def _find_legacy_cache_dir(self, source_dir: Path, workflow_type: str) -> Optional[Path]:
        return find_legacy_cache_dir(source_dir, workflow_type)

    def _scan_novel_progress(self, root: Path) -> Dict[str, Any]:
        return scan_novel_progress(root)

    def _scan_article_progress(self, root: Path) -> Dict[str, Any]:
        return scan_article_progress(root)

    def _scan_splitter_progress(self, root: Path) -> Dict[str, Any]:
        return scan_splitter_progress(root)

    def _unique_stored_name(self, inputs_dir: Path, original_name: str) -> str:
        return unique_stored_name(inputs_dir, original_name)


def _open_directory_with_os(directory: Path) -> None:
    open_directory_with_os(directory, platform=sys.platform, subprocess_module=subprocess)
