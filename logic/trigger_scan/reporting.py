from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from webui_backend.trigger_models import (
    REVIEW_STATUSES,
    ScanFinding,
    ScanReport,
    SkipList,
    SkipListItem,
)


TRIGGER_SCAN_DIR = "trigger_scan"
REPORTS_DIR = "reports"
EXPORTS_DIR = "exports"
REPORT_INDEX_FILENAME = "index.json"
SKIP_LIST_FILENAME = "skip_list.json"
AI_AUXILIARY_WARNING = "AI 扫描结果仅供辅助参考，不能保证发现全部雷点或完全避免误报。"


@dataclass
class ReportHistoryEntry:
    report_id: str
    project_slug: str
    profile_name: str
    scan_mode: str
    scan_range: Dict[str, Any]
    status: str
    created_at: float
    completed_at: float | None = None
    finding_count: int = 0

    @classmethod
    def from_report(cls, report: ScanReport) -> "ReportHistoryEntry":
        return cls(
            report_id=report.report_id,
            project_slug=report.project_slug,
            profile_name=report.profile_name,
            scan_mode=report.scan_mode,
            scan_range=report.scan_range.to_dict(),
            status=report.status,
            created_at=report.created_at,
            completed_at=report.completed_at,
            finding_count=len(report.findings),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportHistoryEntry":
        return cls(
            report_id=str(data.get("report_id", "")),
            project_slug=str(data.get("project_slug", "")),
            profile_name=str(data.get("profile_name", "")),
            scan_mode=str(data.get("scan_mode", "")),
            scan_range=dict(data.get("scan_range", {}) or {}),
            status=str(data.get("status", "")),
            created_at=float(data.get("created_at", 0) or 0),
            completed_at=(
                None
                if data.get("completed_at") is None
                else float(data.get("completed_at", 0) or 0)
            ),
            finding_count=int(data.get("finding_count", 0) or 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "project_slug": self.project_slug,
            "profile_name": self.profile_name,
            "scan_mode": self.scan_mode,
            "scan_range": self.scan_range,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "finding_count": self.finding_count,
        }


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


class TriggerScanReportStore:
    def __init__(self, project_output_dir: str | Path):
        self.project_output_dir = Path(project_output_dir)
        self.scan_dir = self.project_output_dir / TRIGGER_SCAN_DIR
        self.reports_dir = self.scan_dir / REPORTS_DIR
        self.exports_dir = self.scan_dir / EXPORTS_DIR
        self.index_path = self.reports_dir / REPORT_INDEX_FILENAME

    def report_path(self, report_id: str) -> Path:
        return self.reports_dir / f"{report_id}.json"

    def save_report(self, report: ScanReport) -> ScanReport:
        report.validate()
        _write_json(self.report_path(report.report_id), report.to_dict())
        self._upsert_index_entry(ReportHistoryEntry.from_report(report))
        return report

    def save_partial_report(self, report: ScanReport, status: str = "failed") -> ScanReport:
        report.status = status
        if report.completed_at is None:
            report.completed_at = time.time()
        return self.save_report(report)

    def load_report(self, report_id: str) -> ScanReport:
        path = self.report_path(report_id)
        if not path.exists():
            raise ValueError(f"Unknown scan report: {report_id}")
        return ScanReport.from_dict(_read_json(path))

    def delete_report(self, report_id: str) -> None:
        path = self.report_path(report_id)
        if path.exists():
            path.unlink()
        entries = [
            entry
            for entry in self.list_reports()
            if entry.report_id != report_id
        ]
        self._write_index(entries)

    def list_reports(self) -> List[ReportHistoryEntry]:
        if not self.index_path.exists():
            self.rebuild_index()
        data = _read_json(self.index_path)
        entries = [
            ReportHistoryEntry.from_dict(item)
            for item in data.get("items", [])
            if isinstance(item, dict)
        ]
        return sorted(entries, key=lambda item: item.created_at, reverse=True)

    def rebuild_index(self) -> List[ReportHistoryEntry]:
        entries = []
        if self.reports_dir.exists():
            for path in self.reports_dir.glob("*.json"):
                if path.name == REPORT_INDEX_FILENAME:
                    continue
                try:
                    entries.append(ReportHistoryEntry.from_report(ScanReport.from_dict(_read_json(path))))
                except (OSError, ValueError, json.JSONDecodeError):
                    continue
        self._write_index(entries)
        return self.list_reports()

    def update_finding_review(
        self,
        report_id: str,
        finding_id: str,
        *,
        review_status: str | None = None,
        user_note: str | None = None,
    ) -> ScanFinding:
        report = self.load_report(report_id)
        finding = next(
            (item for item in report.findings if item.finding_id == finding_id),
            None,
        )
        if finding is None:
            raise ValueError(f"Unknown finding: {finding_id}")
        if review_status is not None:
            if review_status not in REVIEW_STATUSES:
                raise ValueError("invalid review_status")
            finding.review_status = review_status
        if user_note is not None:
            finding.user_note = user_note
        self.save_report(report)
        return finding

    def export_report_json(self, report_id: str) -> Path:
        report = self.load_report(report_id)
        path = self.exports_dir / f"{report_id}.json"
        _write_json(path, report.to_dict())
        return path

    def export_report_markdown(self, report_id: str) -> Path:
        report = self.load_report(report_id)
        path = self.exports_dir / f"{report_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_report_markdown(report), encoding="utf-8")
        return path

    def _upsert_index_entry(self, entry: ReportHistoryEntry) -> None:
        entries = [
            item
            for item in self.list_reports()
            if item.report_id != entry.report_id
        ]
        entries.append(entry)
        self._write_index(entries)

    def _write_index(self, entries: List[ReportHistoryEntry]) -> None:
        sorted_entries = sorted(entries, key=lambda item: item.created_at, reverse=True)
        _write_json(
            self.index_path,
            {"items": [entry.to_dict() for entry in sorted_entries]},
        )


class SkipListStore:
    def __init__(self, project_output_dir: str | Path, project_slug: str):
        self.project_output_dir = Path(project_output_dir)
        self.project_slug = project_slug
        self.scan_dir = self.project_output_dir / TRIGGER_SCAN_DIR
        self.path = self.scan_dir / SKIP_LIST_FILENAME
        self.exports_dir = self.scan_dir / EXPORTS_DIR

    def load(self) -> SkipList:
        if not self.path.exists():
            return SkipList(
                skip_list_id=f"skip_{self.project_slug}",
                project_slug=self.project_slug,
                created_at=time.time(),
                updated_at=time.time(),
            )
        return SkipList.from_dict(_read_json(self.path))

    def save(self, skip_list: SkipList) -> SkipList:
        skip_list.updated_at = time.time()
        if not skip_list.created_at:
            skip_list.created_at = skip_list.updated_at
        _write_json(self.path, skip_list.to_dict())
        return skip_list

    def add_item(self, item: SkipListItem) -> SkipList:
        skip_list = self.load()
        existing = [
            current
            for current in skip_list.items
            if current.source_finding_id == item.source_finding_id
            and item.source_finding_id
        ]
        if existing:
            index = skip_list.items.index(existing[0])
            skip_list.items[index] = item
        else:
            skip_list.items.append(item)
        return self.save(skip_list)

    def remove_item(self, source_finding_id: str) -> SkipList:
        skip_list = self.load()
        skip_list.items = [
            item for item in skip_list.items if item.source_finding_id != source_finding_id
        ]
        return self.save(skip_list)

    def update_item(self, source_finding_id: str, **changes: Any) -> SkipListItem:
        skip_list = self.load()
        item = next(
            (entry for entry in skip_list.items if entry.source_finding_id == source_finding_id),
            None,
        )
        if item is None:
            raise ValueError(f"Unknown skip-list item: {source_finding_id}")
        for field_name, value in changes.items():
            if hasattr(item, field_name):
                setattr(item, field_name, value)
        self.save(skip_list)
        return item

    def group_by_chapter(self) -> Dict[str, List[SkipListItem]]:
        grouped: Dict[str, List[SkipListItem]] = {}
        for item in self.load().items:
            grouped.setdefault(item.chapter_file, []).append(item)
        return grouped

    def export_markdown(self) -> Path:
        skip_list = self.load()
        path = self.exports_dir / f"{skip_list.skip_list_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_skip_list_markdown(skip_list), encoding="utf-8")
        return path


def _limited_quote(text: str, limit: int) -> str:
    quote = str(text or "").strip()
    if len(quote) <= limit:
        return quote
    return quote[:limit]


def render_report_markdown(report: ScanReport) -> str:
    quote_limit = report.scan_config.max_quote_chars
    lines = [
        f"# 雷点扫描报告 - {report.profile_name}",
        "",
        f"> {AI_AUXILIARY_WARNING}",
        "",
        "## 扫描配置",
        "",
        f"- 扫描模式：{report.scan_mode}",
        f"- 扫描范围：{report.scan_range.start} - {report.scan_range.end or '末尾'}",
        f"- 状态：{report.status}",
        "",
        "## 概览",
        "",
        f"- 发现条目：{len(report.findings)}",
        f"- 聚合事件：{len(report.events)}",
        "",
        "## 雷点事件",
        "",
    ]
    if not report.events:
        lines.append("- 暂无聚合事件")
    for event in report.events:
        lines.extend(
            [
                f"### {event.rule_name}",
                "",
                f"- 涉及章节：{', '.join(event.related_chapters) or event.first_chapter}",
                f"- 最高严重度：{event.max_severity}",
                f"- 最高置信度：{event.max_confidence:.2f}",
                "",
            ]
        )
    lines.extend(["", "## 待复核条目", ""])
    if not report.findings:
        lines.append("- 暂无发现")
    for finding in report.findings:
        detailed = finding.spoiler_levels.detailed
        lines.extend(
            [
                f"### {finding.rule_name} / {finding.chapter_file}",
                "",
                f"- 段落：{', '.join(finding.paragraph_ids)}",
                f"- 严重度：{finding.severity}",
                f"- 置信度：{finding.confidence:.2f}",
                f"- 复核状态：{finding.review_status}",
                f"- 描述：{detailed.description}",
            ]
        )
        quote = _limited_quote(detailed.evidence_quote, quote_limit)
        if quote:
            lines.append(f"- 证据摘录：{quote}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_skip_list_markdown(skip_list: SkipList) -> str:
    grouped: Dict[str, List[SkipListItem]] = {}
    for item in skip_list.items:
        grouped.setdefault(item.chapter_file, []).append(item)

    lines = ["# 跳读清单", ""]
    if not grouped:
        lines.append("- 暂无跳读条目")
        return "\n".join(lines) + "\n"

    for chapter_file in sorted(grouped):
        lines.extend([f"## {chapter_file}", ""])
        for item in grouped[chapter_file]:
            lines.append(
                f"- {item.paragraph_range or '未指定段落'} | {item.rule_name} | 严重度 {item.severity}"
            )
            if item.user_note:
                lines.append(f"  - 备注：{item.user_note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
