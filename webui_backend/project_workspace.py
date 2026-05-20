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
ARTICLE_STATE_FILENAME = "article_summary_state.json"
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


def _read_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _count_text_files(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return len([item for item in path.glob("*.txt") if item.is_file()])


def _project_progress_empty(workflow_type: str) -> Dict[str, Any]:
    return {
        "workflow_type": workflow_type,
        "summary": "暂无进度",
        "percent": 0,
        "stages": [],
    }


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
            "imported_from_path": self.imported_from_path,
            "progress": self.progress or _project_progress_empty(self.workflow_type),
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
        metadata.progress = self.scan_project_progress(metadata)
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
            imported_from_path=str(source_dir),
        )

        inputs_dir = self.inputs_dir(slug)
        output_dir = self.default_export_dir(slug, workflow_type, create=True)
        inputs_dir.mkdir(parents=True, exist_ok=True)
        uploads: List[UploadedFileRef] = []
        for source_file in sorted(source_dir.glob("*.txt"), key=lambda item: item.name):
            if not source_file.is_file():
                continue
            stored_name = self._unique_stored_name(inputs_dir, source_file.name)
            input_target = inputs_dir / stored_name
            output_target = output_dir / stored_name
            shutil.copyfile(source_file, input_target)
            shutil.copyfile(source_file, output_target)
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
        if legacy_cache_dir:
            target_cache = output_dir / ".summarizer_cache"
            if target_cache.exists():
                shutil.rmtree(target_cache)
            shutil.copytree(legacy_cache_dir, target_cache)

        metadata.uploads = uploads
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
        project_name: str = "",
        custom_output_directory: str = "",
        latest_task_id: str = "",
        latest_task_status: str = "",
    ) -> ProjectMetadata:
        metadata = self.load_project(project_slug)
        if project_name.strip():
            metadata.project_name = project_name.strip()
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

    def _load_novel_state(self, root: Path) -> Dict[str, Any]:
        cache_dir = root / ".summarizer_cache"
        task_id_path = cache_dir / "task_id.txt"
        if task_id_path.exists():
            task_id = task_id_path.read_text(encoding="utf-8").strip()
            if task_id:
                state = _read_json_file(cache_dir / f"state_{task_id}.json")
                if state:
                    return state
        state_files = sorted(
            cache_dir.glob("state_*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        return _read_json_file(state_files[0]) if state_files else {}

    def _scan_novel_progress(self, root: Path) -> Dict[str, Any]:
        total_chapters = _count_text_files(root)
        state = self._load_novel_state(root)
        small_completed = len([value for value in state.get("small_summary", {}).values() if value])
        big_plot = len([value for key, value in state.get("big_summary", {}).items() if value and key.endswith("_plot")])
        big_char = len([value for key, value in state.get("big_summary", {}).items() if value and key.endswith("_char")])
        super_completed = sum(
            len([value for value in value_map.values() if value])
            for stage, value_map in state.items()
            if stage.startswith("super_summary") and isinstance(value_map, dict)
        )
        ultimate_completed = len([value for value in state.get("ultimate_summary", {}).values() if value])
        stages = [
            {"label": "小总结", "completed": small_completed, "total": total_chapters},
            {"label": "大总结-剧情", "completed": big_plot, "total": None},
            {"label": "大总结-角色", "completed": big_char, "total": None},
            {"label": "超级总结", "completed": super_completed, "total": None},
            {"label": "终极总结", "completed": ultimate_completed, "total": 4},
        ]
        percent = 0
        if total_chapters > 0:
            percent = min(95, int((small_completed / total_chapters) * 35))
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
