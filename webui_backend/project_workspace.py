from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .file_services import safe_filename


WORKFLOW_EXPORT_SUBDIRS = {
    "novel_summary": "novel-summary",
    "article_summary": "article-summary",
    "custom_summary": "custom-summary",
    "chapter_split": "chapter-split",
}
PROJECT_METADATA_FILENAME = "project.json"
ALLOWED_UPLOAD_SUFFIXES = {".txt"}
MAX_UPLOAD_FILE_BYTES = 10 * 1024 * 1024
MAX_UPLOAD_BATCH_BYTES = 50 * 1024 * 1024


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
    uploads: List[UploadedFileRef] = field(default_factory=list)
    latest_task_id: str = ""
    latest_task_status: str = ""
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
            uploads=[UploadedFileRef.from_dict(item) for item in data.get("uploads", [])],
            latest_task_id=str(data.get("latest_task_id", "")),
            latest_task_status=str(data.get("latest_task_status", "")),
            created_at=float(data.get("created_at", current_timestamp())),
            updated_at=float(data.get("updated_at", current_timestamp())),
        )

    def to_dict(self) -> Dict[str, Any]:
        missing_uploads = [
            upload.original_name for upload in self.uploads if not Path(upload.path).exists()
        ]
        return {
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            "workflow_type": self.workflow_type,
            "default_output_directory": self.default_output_directory,
            "custom_output_directory": self.custom_output_directory,
            "uploads": [upload.to_dict() for upload in self.uploads],
            "upload_count": len(self.uploads),
            "latest_task_id": self.latest_task_id,
            "latest_task_status": self.latest_task_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "warnings": [
                f"缺失上传文件：{name}" for name in missing_uploads
            ],
        }


class ProjectWorkspaceService:
    def __init__(self, runtime_base_path: str | Path) -> None:
        self.runtime_base_path = Path(runtime_base_path)

    @property
    def workspace_root(self) -> Path:
        return self.runtime_base_path / "workspace" / "projects"

    @property
    def exports_root(self) -> Path:
        return self.runtime_base_path / "exports"

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
        path = self.exports_root / project_slug
        if workflow_type:
            path = path / workflow_export_subdir(workflow_type)
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

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
        path = self.metadata_path(metadata.project_slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata.to_dict(), handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)

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
            projects.append(metadata)
        return sorted(projects, key=lambda item: item.updated_at, reverse=True)

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

    def resolve_output_dir(
        self,
        *,
        project_slug: str,
        workflow_type: str,
        custom_output_directory: str = "",
        create: bool = True,
    ) -> Path:
        custom = custom_output_directory.strip()
        if custom:
            path = Path(custom).expanduser().resolve(strict=False)
            if path.exists() and not path.is_dir():
                raise ValueError("自定义输出路径必须是目录")
            if create:
                path.mkdir(parents=True, exist_ok=True)
            return path
        return self.default_export_dir(project_slug, workflow_type, create=create)

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
        custom_output_directory: str = "",
        latest_task_id: str = "",
        latest_task_status: str = "",
    ) -> ProjectMetadata:
        metadata = self.load_project(project_slug)
        metadata.custom_output_directory = custom_output_directory
        if latest_task_id:
            metadata.latest_task_id = latest_task_id
        if latest_task_status:
            metadata.latest_task_status = latest_task_status
        self.save_project(metadata)
        return metadata

    def open_directory(self, path: str | Path, *, create: bool = False) -> None:
        directory = Path(path).expanduser().resolve(strict=False)
        if directory.exists() and not directory.is_dir():
            raise ValueError("路径不是目录")
        if create:
            directory.mkdir(parents=True, exist_ok=True)
        if not directory.exists():
            raise ValueError("目录不存在")
        _open_directory_with_os(directory)

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
