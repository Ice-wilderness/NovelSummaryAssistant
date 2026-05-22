from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, List

from logic.utils import get_summarizer_cache_dir, read_file_content_robustly


PARAGRAPH_INDEX_SUBDIR = "paragraph_index"
DEFAULT_MAX_CHUNK_CHARS = 12000


@dataclass
class IndexedParagraph:
    id: str
    text: str
    line_number: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IndexedParagraph":
        return cls(
            id=str(data.get("id", "")),
            text=str(data.get("text", "")),
            line_number=int(data.get("line_number", 0) or 0),
        )


@dataclass
class ParagraphChunk:
    id: str
    paragraph_ids: List[str]
    start_paragraph_id: str
    end_paragraph_id: str
    text: str
    source_char_count: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParagraphChunk":
        paragraph_ids = [str(item) for item in data.get("paragraph_ids", [])]
        return cls(
            id=str(data.get("id", "")),
            paragraph_ids=paragraph_ids,
            start_paragraph_id=str(data.get("start_paragraph_id", "")),
            end_paragraph_id=str(data.get("end_paragraph_id", "")),
            text=str(data.get("text", "")),
            source_char_count=int(data.get("source_char_count", 0) or 0),
        )


@dataclass
class ChapterParagraphIndex:
    chapter_path: str
    chapter_file: str
    chapter_title: str
    file_size: int
    modified_time_ns: int
    content_hash: str
    max_chunk_chars: int
    paragraphs: List[IndexedParagraph] = field(default_factory=list)
    chunks: List[ParagraphChunk] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)
    cache_hit: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChapterParagraphIndex":
        return cls(
            chapter_path=str(data.get("chapter_path", "")),
            chapter_file=str(data.get("chapter_file", "")),
            chapter_title=str(data.get("chapter_title", "")),
            file_size=int(data.get("file_size", 0) or 0),
            modified_time_ns=int(data.get("modified_time_ns", 0) or 0),
            content_hash=str(data.get("content_hash", "")),
            max_chunk_chars=int(data.get("max_chunk_chars", DEFAULT_MAX_CHUNK_CHARS) or DEFAULT_MAX_CHUNK_CHARS),
            paragraphs=[
                IndexedParagraph.from_dict(item)
                for item in data.get("paragraphs", [])
            ],
            chunks=[ParagraphChunk.from_dict(item) for item in data.get("chunks", [])],
            generated_at=float(data.get("generated_at", time.time()) or time.time()),
            cache_hit=bool(data.get("cache_hit", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["cache_hit"] = False
        return data


@dataclass
class ParagraphContext:
    paragraph_ids: List[str]
    matched_paragraph_ids: List[str]
    missing_paragraph_ids: List[str]
    paragraphs: List[IndexedParagraph]
    text: str


def get_paragraph_index_cache_dir(novel_folder_path: str | os.PathLike[str]) -> Path:
    cache_dir = Path(get_summarizer_cache_dir(str(novel_folder_path))) / PARAGRAPH_INDEX_SUBDIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def extract_chapter_title(content: str, fallback_name: str = "") -> str:
    for line in content.splitlines():
        title = line.strip()
        if title:
            return title
    return Path(fallback_name).stem if fallback_name else ""


def split_paragraphs(content: str) -> List[IndexedParagraph]:
    paragraphs: List[IndexedParagraph] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        paragraphs.append(
            IndexedParagraph(
                id=f"P{len(paragraphs) + 1:03d}",
                text=text,
                line_number=line_number,
            )
        )
    return paragraphs


def _chapter_cache_key(chapter_path: Path) -> str:
    identity = str(chapter_path.resolve(strict=False)).encode("utf-8")
    return hashlib.sha1(identity).hexdigest()


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _build_chunks(
    paragraphs: List[IndexedParagraph],
    max_chunk_chars: int,
) -> List[ParagraphChunk]:
    chunks: List[ParagraphChunk] = []
    current: List[IndexedParagraph] = []
    current_chars = 0
    effective_limit = max(1, int(max_chunk_chars or DEFAULT_MAX_CHUNK_CHARS))

    def flush() -> None:
        nonlocal current, current_chars
        if not current:
            return
        text = "\n".join(f"{paragraph.id} {paragraph.text}" for paragraph in current)
        chunks.append(
            ParagraphChunk(
                id=f"C{len(chunks) + 1:03d}",
                paragraph_ids=[paragraph.id for paragraph in current],
                start_paragraph_id=current[0].id,
                end_paragraph_id=current[-1].id,
                text=text,
                source_char_count=sum(len(paragraph.text) for paragraph in current),
            )
        )
        current = []
        current_chars = 0

    for paragraph in paragraphs:
        projected_chars = current_chars + len(paragraph.text)
        if current and projected_chars > effective_limit:
            flush()
        current.append(paragraph)
        current_chars += len(paragraph.text)

    flush()
    return chunks


def _cache_path(
    chapter_path: Path,
    novel_folder_path: str | os.PathLike[str],
) -> Path:
    return get_paragraph_index_cache_dir(novel_folder_path) / f"{_chapter_cache_key(chapter_path)}.json"


def _load_cached_index(
    cache_path: Path,
    *,
    chapter_path: Path,
    file_size: int,
    modified_time_ns: int,
    content_hash: str,
    max_chunk_chars: int,
) -> ChapterParagraphIndex | None:
    if not cache_path.exists():
        return None
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            cached = ChapterParagraphIndex.from_dict(json.load(handle))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None

    if (
        Path(cached.chapter_path).resolve(strict=False) != chapter_path.resolve(strict=False)
        or cached.file_size != file_size
        or cached.modified_time_ns != modified_time_ns
        or cached.content_hash != content_hash
        or cached.max_chunk_chars != max_chunk_chars
    ):
        return None
    cached.cache_hit = True
    return cached


def build_chapter_paragraph_index(
    chapter_path: str | os.PathLike[str],
    *,
    novel_folder_path: str | os.PathLike[str] | None = None,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    use_cache: bool = True,
) -> ChapterParagraphIndex:
    path = Path(chapter_path)
    novel_root = Path(novel_folder_path) if novel_folder_path is not None else path.parent
    stat = path.stat()
    content = read_file_content_robustly(str(path))
    content_digest = _content_hash(content)
    effective_max_chunk_chars = max(1, int(max_chunk_chars or DEFAULT_MAX_CHUNK_CHARS))
    cache_path = _cache_path(path, novel_root)

    if use_cache:
        cached = _load_cached_index(
            cache_path,
            chapter_path=path,
            file_size=stat.st_size,
            modified_time_ns=stat.st_mtime_ns,
            content_hash=content_digest,
            max_chunk_chars=effective_max_chunk_chars,
        )
        if cached is not None:
            return cached

    paragraphs = split_paragraphs(content)
    chapter_index = ChapterParagraphIndex(
        chapter_path=str(path.resolve(strict=False)),
        chapter_file=path.name,
        chapter_title=extract_chapter_title(content, path.name),
        file_size=stat.st_size,
        modified_time_ns=stat.st_mtime_ns,
        content_hash=content_digest,
        max_chunk_chars=effective_max_chunk_chars,
        paragraphs=paragraphs,
        chunks=_build_chunks(paragraphs, effective_max_chunk_chars),
        cache_hit=False,
    )
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(chapter_index.to_dict(), handle, ensure_ascii=False, indent=2)
    return chapter_index


def build_project_paragraph_indexes(
    chapter_paths: Iterable[str | os.PathLike[str]],
    *,
    novel_folder_path: str | os.PathLike[str],
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    use_cache: bool = True,
) -> List[ChapterParagraphIndex]:
    return [
        build_chapter_paragraph_index(
            chapter_path,
            novel_folder_path=novel_folder_path,
            max_chunk_chars=max_chunk_chars,
            use_cache=use_cache,
        )
        for chapter_path in chapter_paths
    ]


def extract_paragraph_context(
    chapter_index: ChapterParagraphIndex,
    paragraph_ids: Iterable[str],
    *,
    before: int = 1,
    after: int = 1,
) -> ParagraphContext:
    requested_ids = [str(paragraph_id) for paragraph_id in paragraph_ids]
    index_by_id = {
        paragraph.id: position
        for position, paragraph in enumerate(chapter_index.paragraphs)
    }
    matched_positions = [
        index_by_id[paragraph_id]
        for paragraph_id in requested_ids
        if paragraph_id in index_by_id
    ]
    missing_ids = [
        paragraph_id for paragraph_id in requested_ids if paragraph_id not in index_by_id
    ]

    if not matched_positions:
        return ParagraphContext(
            paragraph_ids=[],
            matched_paragraph_ids=[],
            missing_paragraph_ids=missing_ids,
            paragraphs=[],
            text="",
        )

    start = max(min(matched_positions) - max(0, before), 0)
    end = min(max(matched_positions) + max(0, after) + 1, len(chapter_index.paragraphs))
    paragraphs = chapter_index.paragraphs[start:end]
    return ParagraphContext(
        paragraph_ids=[paragraph.id for paragraph in paragraphs],
        matched_paragraph_ids=[
            paragraph_id for paragraph_id in requested_ids if paragraph_id in index_by_id
        ],
        missing_paragraph_ids=missing_ids,
        paragraphs=paragraphs,
        text="\n".join(f"{paragraph.id} {paragraph.text}" for paragraph in paragraphs),
    )
