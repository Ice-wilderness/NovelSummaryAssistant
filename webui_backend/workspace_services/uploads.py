from __future__ import annotations

import shutil
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

from webui_backend.file_services import safe_filename

from .low_state import current_timestamp


ALLOWED_UPLOAD_SUFFIXES = {".txt"}
MAX_UPLOAD_FILE_BYTES = 100 * 1024 * 1024
MAX_UPLOAD_BATCH_BYTES = 100 * 1024 * 1024


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


def unique_stored_name(inputs_dir: Path, original_name: str) -> str:
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


def store_text_uploads(
    *,
    project_slug: str,
    inputs_dir: Path,
    files: Iterable[Dict[str, Any]],
) -> List[UploadedFileRef]:
    incoming = list(files)
    if not incoming:
        raise ValueError("请至少选择一个文本文件")

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

        stored_name = unique_stored_name(inputs_dir, original_name)
        target = inputs_dir / stored_name
        target.write_bytes(encoded)
        uploads.append(
            UploadedFileRef(
                id=uuid.uuid4().hex,
                project_slug=project_slug,
                original_name=original_name,
                stored_name=stored_name,
                path=str(target),
                size=size,
            )
        )
    return uploads


def resolve_upload_refs(
    *,
    uploads: Iterable[UploadedFileRef],
    upload_ids: Iterable[str],
) -> List[UploadedFileRef]:
    requested = [str(upload_id) for upload_id in upload_ids if str(upload_id).strip()]
    if not requested:
        raise ValueError("uploaded_file_ids is required")
    upload_map = {upload.id: upload for upload in uploads}
    resolved: List[UploadedFileRef] = []
    for upload_id in requested:
        upload = upload_map.get(upload_id)
        if upload is None:
            raise ValueError(f"未知上传文件引用：{upload_id}")
        if not Path(upload.path).exists():
            raise ValueError(f"上传文件已缺失：{upload.original_name}")
        resolved.append(upload)
    return resolved


def remove_upload_files(uploads: Iterable[UploadedFileRef]) -> None:
    for upload in uploads:
        try:
            Path(upload.path).unlink(missing_ok=True)
        except OSError:
            continue


def select_upload_refs(
    *,
    uploads: Iterable[UploadedFileRef],
    upload_ids: Iterable[str],
) -> tuple[List[UploadedFileRef], List[UploadedFileRef]]:
    requested_ids = [str(upload_id) for upload_id in upload_ids]
    upload_map = {upload.id: upload for upload in uploads}
    unknown_ids = [upload_id for upload_id in requested_ids if upload_id not in upload_map]
    if unknown_ids:
        raise ValueError(f"未知上传文件引用：{unknown_ids[0]}")
    removed_uploads = [upload for upload in uploads if upload.id not in requested_ids]
    selected_uploads = [upload_map[upload_id] for upload_id in requested_ids]
    return selected_uploads, removed_uploads


def refs_for_existing_files(
    *,
    project_slug: str,
    files: Iterable[Path],
) -> List[UploadedFileRef]:
    uploads: List[UploadedFileRef] = []
    for file_path in files:
        uploads.append(
            UploadedFileRef(
                id=uuid.uuid4().hex,
                project_slug=project_slug,
                original_name=file_path.name,
                stored_name=file_path.name,
                path=str(file_path),
                size=file_path.stat().st_size,
            )
        )
    return uploads


def uploaded_ref_for_file(
    *,
    project_slug: str,
    original_name: str,
    stored_name: str,
    path: Path,
) -> UploadedFileRef:
    return UploadedFileRef(
        id=uuid.uuid4().hex,
        project_slug=project_slug,
        original_name=original_name,
        stored_name=stored_name,
        path=str(path),
        size=path.stat().st_size,
    )


def prepare_copied_inputs(output_dir: Path, uploads: Iterable[UploadedFileRef]) -> List[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    copied_names: List[str] = []
    for upload in uploads:
        target = output_dir / upload.stored_name
        shutil.copyfile(upload.path, target)
        copied_names.append(upload.stored_name)
    return copied_names
