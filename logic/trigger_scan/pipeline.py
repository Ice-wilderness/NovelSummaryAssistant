from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from logic.paragraph_index import ChapterParagraphIndex
from logic.prompts import USER_FACING_SMALL_CHAR_SUBDIR, USER_FACING_SMALL_PLOT_SUBDIR
from logic.utils import (
    find_and_sort_chapter_files,
    get_summarizer_cache_dir,
    natural_sort_key,
    read_file_content_robustly,
)
from webui_backend.trigger_models import (
    ScanEvent,
    ScanFinding,
    SpoilerLevels,
    TriggerProfile,
    TriggerRule,
    TriggerScanConfig,
)

from .json_utils import TriggerScanJsonError, require_json_list, require_json_object
from .scan_state import ScanState, ScanStateStore


SUMMARY_SUFFIXES = (".md", ".txt")
LEGACY_RANGE_PATTERN = re.compile(r"第\s*[一二三四五六七八九十百千万亿零\d]+\s*章\s*[-–—~_至到]+\s*(?:第\s*)?[一二三四五六七八九十百千万亿零\d]+\s*章")
CHAPTER_HEADING_PATTERN = re.compile(r"^\s*第\s*[一二三四五六七八九十百千万亿零\d]+\s*(?:章|节|回)", re.MULTILINE)


@dataclass
class SmallSummaryCoverage:
    covered_chapters: List[str] = field(default_factory=list)
    missing_chapters: List[str] = field(default_factory=list)
    summary_files: List[str] = field(default_factory=list)


@dataclass
class ScanStartupResult:
    ready: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    chapter_files: List[str] = field(default_factory=list)
    selected_chapter_files: List[str] = field(default_factory=list)
    missing_summary_chapters: List[str] = field(default_factory=list)


@dataclass
class CoarseScanResult:
    suspected_chapters: List[str]
    suspected_rule_ids: List[str]


def _enabled_rules(profile: TriggerProfile) -> List[TriggerRule]:
    return [rule for rule in profile.rules if rule.enabled]


def _batch_items(items: Sequence[Any], batch_size: int) -> List[List[Any]]:
    size = max(int(batch_size or 1), 1)
    return [list(items[index:index + size]) for index in range(0, len(items), size)]


def _chapter_number(path: str) -> int:
    key = natural_sort_key(os.path.basename(path))
    for part in key:
        if isinstance(part, int):
            return part
    return 999999


def _select_scan_range(chapter_files: List[str], config: TriggerScanConfig) -> List[str]:
    config.scan_range.validate()
    start = config.scan_range.start
    end = config.scan_range.end
    selected = []
    for position, chapter_file in enumerate(chapter_files, start=1):
        chapter_no = _chapter_number(chapter_file)
        comparable = chapter_no if chapter_no != 999999 else position
        if comparable < start:
            continue
        if end is not None and comparable > end:
            continue
        selected.append(chapter_file)
    return selected


def _requires_granularity_migration(chapter_files: Iterable[str]) -> bool:
    for chapter_file in chapter_files:
        path = Path(chapter_file)
        if LEGACY_RANGE_PATTERN.search(path.name):
            return True
        try:
            headings = CHAPTER_HEADING_PATTERN.findall(read_file_content_robustly(str(path)))
        except Exception:
            headings = []
        if len(headings) > 1:
            return True
    return False


def _summary_files(path: Path) -> Dict[str, Path]:
    if not path.exists() or not path.is_dir():
        return {}
    files: Dict[str, Path] = {}
    for suffix in SUMMARY_SUFFIXES:
        for item in path.glob(f"*{suffix}"):
            if item.is_file():
                files[item.stem] = item
    return files


def _summary_stem_for_chapter(chapter_file: str) -> str:
    return Path(chapter_file).stem


def _small_batch_range(stem: str) -> tuple[str, str] | None:
    match = re.match(r"^small_batch_(.+)_to_(.+)$", stem)
    if not match:
        return None
    return match.group(1), match.group(2)


def _covered_stems_from_summary(stem: str, chapter_stems: List[str]) -> List[str]:
    batch_range = _small_batch_range(stem)
    if not batch_range:
        return [stem]
    start, end = batch_range
    try:
        start_index = chapter_stems.index(start)
        end_index = chapter_stems.index(end)
    except ValueError:
        return []
    if end_index < start_index:
        return []
    return chapter_stems[start_index:end_index + 1]


def discover_small_summary_coverage(
    novel_folder_path: str | os.PathLike[str],
    chapter_files: Iterable[str],
) -> SmallSummaryCoverage:
    cache_dir = Path(get_summarizer_cache_dir(str(novel_folder_path)))
    plot_files = _summary_files(cache_dir / USER_FACING_SMALL_PLOT_SUBDIR)
    char_files = _summary_files(cache_dir / USER_FACING_SMALL_CHAR_SUBDIR)
    chapter_list = [str(item) for item in chapter_files]
    chapter_stems = [_summary_stem_for_chapter(item) for item in chapter_list]
    covered_stems: set[str] = set()
    summary_paths: List[str] = []

    for stem in sorted(set(plot_files) & set(char_files), key=natural_sort_key):
        stems = _covered_stems_from_summary(stem, chapter_stems)
        if not stems:
            continue
        covered_stems.update(stems)
        summary_paths.extend([str(plot_files[stem]), str(char_files[stem])])

    covered_chapters = [
        chapter_file
        for chapter_file, stem in zip(chapter_list, chapter_stems)
        if stem in covered_stems
    ]
    missing_chapters = [
        chapter_file
        for chapter_file, stem in zip(chapter_list, chapter_stems)
        if stem not in covered_stems
    ]
    return SmallSummaryCoverage(
        covered_chapters=covered_chapters,
        missing_chapters=missing_chapters,
        summary_files=sorted(summary_paths, key=natural_sort_key),
    )


def validate_scan_startup(
    *,
    novel_folder_path: str | os.PathLike[str],
    profile: TriggerProfile,
    config: TriggerScanConfig,
    available_api_ids: Iterable[str] | None = None,
    scan_state: ScanState | None = None,
    config_snapshot: Dict[str, Any] | None = None,
    profile_version: str = "",
) -> ScanStartupResult:
    errors: List[str] = []
    warnings: List[str] = []
    try:
        profile.validate()
        config.validate()
    except ValueError as exc:
        errors.append(str(exc))

    enabled_rules = _enabled_rules(profile)
    if not enabled_rules:
        errors.append("trigger profile has no enabled rules")

    available = set(str(item) for item in (available_api_ids or []))
    if available:
        missing_scan_apis = [api_id for api_id in config.scan_api_ids if api_id not in available]
        if missing_scan_apis:
            errors.append(f"unknown scan API: {', '.join(missing_scan_apis)}")
        if config.verification_api_id and config.verification_api_id not in available:
            errors.append(f"unknown verification API: {config.verification_api_id}")

    chapter_files = find_and_sort_chapter_files(
        str(novel_folder_path),
        lambda *_args, **_kwargs: None,
    )
    if not chapter_files:
        errors.append("no readable chapter files")
        return ScanStartupResult(False, errors, warnings, [], [], [])
    if _requires_granularity_migration(chapter_files):
        errors.append("chapter granularity migration is required")

    selected = _select_scan_range(chapter_files, config)
    if not selected:
        errors.append("scan range does not include any chapters")

    if scan_state is not None:
        snapshot = config_snapshot if config_snapshot is not None else config.to_dict()
        if ScanStateStore.is_compatible(
            scan_state,
            config_snapshot=snapshot,
            profile_version=profile_version,
        ):
            warnings.append("resumable scan state available")
        else:
            warnings.append("existing scan state is incompatible")

    missing_summary_chapters: List[str] = []
    if config.scan_mode == "hybrid" and selected:
        coverage = discover_small_summary_coverage(novel_folder_path, selected)
        missing_summary_chapters = coverage.missing_chapters
        if missing_summary_chapters:
            errors.append("hybrid scan requires small summary coverage")

    return ScanStartupResult(
        ready=not errors,
        errors=errors,
        warnings=warnings,
        chapter_files=chapter_files,
        selected_chapter_files=selected,
        missing_summary_chapters=missing_summary_chapters,
    )


def build_coarse_summary_batches(
    summary_files: Sequence[str],
    config: TriggerScanConfig,
) -> List[List[str]]:
    batch_size = getattr(config, "coarse_summary_batch_size", config.coarse_batch_size)
    return _batch_items([str(item) for item in summary_files], batch_size)


def build_precise_chapter_batches(
    chapter_files: Sequence[str],
    config: TriggerScanConfig,
) -> List[List[str]]:
    return _batch_items([str(item) for item in chapter_files], config.precise_chapter_batch_size)


def parse_coarse_scan_response(
    model_output: str,
    *,
    valid_chapter_files: Iterable[str],
    valid_rule_ids: Iterable[str],
) -> CoarseScanResult:
    payload = require_json_object(model_output)
    valid_chapters = {Path(item).name for item in valid_chapter_files}
    valid_rules = {str(item) for item in valid_rule_ids}
    chapters = []
    rules = []
    for item in payload.get("suspected_chapters", []):
        chapter = str(item)
        if chapter in valid_chapters and chapter not in chapters:
            chapters.append(chapter)
    for item in payload.get("suspected_rule_ids", []):
        rule_id = str(item)
        if rule_id in valid_rules and rule_id not in rules:
            rules.append(rule_id)
    return CoarseScanResult(suspected_chapters=chapters, suspected_rule_ids=rules)


def _rule_lookup(profile: TriggerProfile) -> Dict[str, TriggerRule]:
    return {rule.id: rule for rule in profile.rules}


def _valid_paragraph_ids(chapter_index: ChapterParagraphIndex) -> set[str]:
    return {paragraph.id for paragraph in chapter_index.paragraphs}


def _normalize_raw_finding(raw: Dict[str, Any], config: TriggerScanConfig) -> Dict[str, Any]:
    required_fields = ["rule_id", "severity", "confidence", "paragraph_ids", "spoiler_levels"]
    for field_name in required_fields:
        if field_name not in raw:
            raise TriggerScanJsonError(f"finding missing required field: {field_name}")
    if "is_main_plot" not in raw and "main_plot" not in raw:
        raise TriggerScanJsonError("finding missing required field: is_main_plot")
    normalized = dict(raw)
    if "is_main_plot" not in normalized:
        normalized["is_main_plot"] = bool(normalized.get("main_plot"))

    spoiler_levels = normalized.get("spoiler_levels")
    if not isinstance(spoiler_levels, dict):
        raise TriggerScanJsonError("spoiler_levels must be a JSON object")
    for level in ["low", "standard", "detailed"]:
        if level not in spoiler_levels or not isinstance(spoiler_levels[level], dict):
            raise TriggerScanJsonError(f"spoiler_levels.{level} is required")
    evidence_quote = str(spoiler_levels["detailed"].get("evidence_quote", "")).strip()
    if not evidence_quote:
        raise TriggerScanJsonError("detailed evidence_quote is required")
    if len(evidence_quote) > config.max_quote_chars:
        raise TriggerScanJsonError("detailed evidence_quote exceeds max_quote_chars")
    return normalized


def parse_precise_scan_findings(
    model_output: str,
    *,
    chapter_index: ChapterParagraphIndex,
    profile: TriggerProfile,
    config: TriggerScanConfig,
) -> List[ScanFinding]:
    raw_findings = require_json_list(model_output)
    rules = _rule_lookup(profile)
    valid_paragraphs = _valid_paragraph_ids(chapter_index)
    findings: List[ScanFinding] = []
    for raw in raw_findings:
        if not isinstance(raw, dict):
            raise TriggerScanJsonError("finding item must be a JSON object")
        raw = _normalize_raw_finding(raw, config)
        rule_id = str(raw.get("rule_id", "")).strip()
        rule = rules.get(rule_id)
        if rule is None:
            raise TriggerScanJsonError(f"unknown rule_id: {rule_id}")
        paragraph_ids = [str(item) for item in raw.get("paragraph_ids", [])]
        if not paragraph_ids or any(paragraph_id not in valid_paragraphs for paragraph_id in paragraph_ids):
            raise TriggerScanJsonError("finding contains invalid paragraph_ids")
        finding = ScanFinding.from_dict(
            {
                **raw,
                "finding_id": str(raw.get("finding_id") or f"finding_{uuid.uuid4().hex}"),
                "rule_name": rule.name,
                "chapter_file": chapter_index.chapter_file,
                "chapter_title": chapter_index.chapter_title,
                "paragraph_ids": paragraph_ids,
                "spoiler_levels": raw.get("spoiler_levels", {}),
            }
        )
        finding.to_dict()
        findings.append(finding)
    return apply_finding_filters(findings, profile, config)


def apply_finding_filters(
    findings: Iterable[ScanFinding],
    profile: TriggerProfile,
    config: TriggerScanConfig,
) -> List[ScanFinding]:
    rules = _rule_lookup(profile)
    retained: List[ScanFinding] = []
    for finding in findings:
        rule = rules.get(finding.rule_id)
        if rule is None or not rule.enabled:
            continue
        if finding.severity < rule.severity_threshold:
            continue
        if finding.confidence < config.min_confidence and not config.keep_low_confidence:
            continue
        retained.append(finding)
    return retained


def build_verification_batches(
    findings: Sequence[ScanFinding],
    config: TriggerScanConfig,
) -> List[List[ScanFinding]]:
    groups: Dict[str, List[ScanFinding]] = {}
    for finding in findings:
        groups.setdefault(finding.chapter_file, []).append(finding)
    ordered_groups = [
        groups[key]
        for key in sorted(groups, key=natural_sort_key)
    ]
    return [
        [finding for group in batch for finding in group]
        for batch in _batch_items(ordered_groups, config.verification_chapter_batch_size)
    ]


def apply_verification_results(
    findings: Sequence[ScanFinding],
    model_output: str,
    *,
    retain_false_positives: bool = False,
) -> List[ScanFinding]:
    verdicts = require_json_list(model_output)
    verdict_by_id = {
        str(item.get("finding_id")): str(item.get("verdict", "")).strip()
        for item in verdicts
        if isinstance(item, dict)
    }
    verified: List[ScanFinding] = []
    for finding in findings:
        verdict = verdict_by_id.get(finding.finding_id, "confirmed")
        if verdict == "false_positive":
            if retain_false_positives:
                finding.review_status = "false_positive"
                verified.append(finding)
            continue
        finding.review_status = "confirmed"
        verified.append(finding)
    return verified


def _paragraph_number(paragraph_id: str) -> int:
    match = re.search(r"(\d+)", paragraph_id)
    return int(match.group(1)) if match else 0


def _are_adjacent(ids_a: Sequence[str], ids_b: Sequence[str]) -> bool:
    if not ids_a or not ids_b:
        return False
    return _paragraph_number(ids_b[0]) <= _paragraph_number(ids_a[-1]) + 1


def merge_adjacent_findings(findings: Sequence[ScanFinding]) -> List[ScanFinding]:
    sorted_findings = sorted(
        findings,
        key=lambda item: (natural_sort_key(item.chapter_file), item.rule_id, _paragraph_number(item.paragraph_ids[0])),
    )
    merged: List[ScanFinding] = []
    for finding in sorted_findings:
        if (
            merged
            and merged[-1].chapter_file == finding.chapter_file
            and merged[-1].rule_id == finding.rule_id
            and _are_adjacent(merged[-1].paragraph_ids, finding.paragraph_ids)
        ):
            merged[-1].paragraph_ids = sorted(
                set(merged[-1].paragraph_ids + finding.paragraph_ids),
                key=_paragraph_number,
            )
            merged[-1].severity = max(merged[-1].severity, finding.severity)
            merged[-1].confidence = max(merged[-1].confidence, finding.confidence)
            continue
        merged.append(finding)
    return merged


def aggregate_findings_into_events(findings: Sequence[ScanFinding]) -> List[ScanEvent]:
    events: List[ScanEvent] = []
    grouped: Dict[str, List[ScanFinding]] = {}
    for finding in findings:
        grouped.setdefault(finding.rule_id, []).append(finding)

    for rule_id, group in sorted(grouped.items()):
        ordered = sorted(group, key=lambda item: natural_sort_key(item.chapter_file))
        events.append(
            ScanEvent(
                event_id=f"event_{uuid.uuid4().hex}",
                rule_id=rule_id,
                rule_name=ordered[0].rule_name,
                first_chapter=ordered[0].chapter_file,
                related_chapters=sorted(
                    {finding.chapter_file for finding in ordered},
                    key=natural_sort_key,
                ),
                max_severity=max(finding.severity for finding in ordered),
                max_confidence=max(finding.confidence for finding in ordered),
                is_main_plot=any(finding.is_main_plot for finding in ordered),
                finding_ids=[finding.finding_id for finding in ordered],
            )
        )
    return events
