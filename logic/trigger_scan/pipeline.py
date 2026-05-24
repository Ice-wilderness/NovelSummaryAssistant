from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence

from logic.paragraph_index import ChapterParagraphIndex
from logic.utils import (
    find_and_sort_chapter_files,
    natural_sort_key,
)
from webui_backend.trigger_models import (
    ScanEvent,
    ScanFinding,
    SpoilerLevels,
    TriggerProfile,
    TriggerRule,
    TriggerScanConfig,
)

from .json_utils import TriggerScanJsonError, require_json_list
from .scan_state import ScanState, ScanStateStore


@dataclass
class ScanStartupResult:
    ready: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    chapter_files: List[str] = field(default_factory=list)
    selected_chapter_files: List[str] = field(default_factory=list)
    resumable_state: ScanState | None = None
    pending_chapter_files: List[str] = field(default_factory=list)


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


def validate_scan_startup(
    *,
    novel_folder_path: str | os.PathLike[str],
    profile: TriggerProfile,
    config: TriggerScanConfig,
    available_api_ids: Iterable[str] | None = None,
    scan_state: ScanState | None = None,
    config_snapshot: Dict[str, Any] | None = None,
    profile_version: str = "",
    resume_from_report_id: str = "",
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
        return ScanStartupResult(False, errors, warnings, [], [])

    selected = _select_scan_range(chapter_files, config)
    if not selected:
        errors.append("scan range does not include any chapters")

    snapshot = config_snapshot if config_snapshot is not None else {
        "scan_mode": config.scan_mode,
        "scan_range": {"start": config.scan_range.start, "end": config.scan_range.end},
        "scan_api_ids": list(config.scan_api_ids),
        "min_confidence": config.min_confidence,
        "keep_low_confidence": config.keep_low_confidence,
        "verification_enabled": config.verification_enabled,
        "verification_api_id": config.verification_api_id,
        "precise_chapter_batch_size": config.precise_chapter_batch_size,
        "verification_chapter_batch_size": config.verification_chapter_batch_size,
        "max_quote_chars": config.max_quote_chars,
        "generate_skip_advice": config.generate_skip_advice,
        "minimum_output_characters": config.minimum_output_characters,
    }

    # Only attempt resume when explicitly requested via resume_from_report_id
    if resume_from_report_id and scan_state is None:
        # report_id = "report_" + task_id → derive task_id
        derived_task_id = resume_from_report_id.removeprefix("report_")
        if derived_task_id and derived_task_id != resume_from_report_id:
            scan_state = ScanStateStore(
                str(novel_folder_path), derived_task_id
            ).load()

    pending_chapters = list(selected)
    if scan_state is not None:
        if ScanStateStore.is_compatible(
            scan_state,
            config_snapshot=snapshot,
            profile_version=profile_version,
        ):
            pending_chapters = ScanStateStore.pending_chapters(
                selected or chapter_files,
                scan_state,
                config_snapshot=snapshot,
                profile_version=profile_version,
            )
            if pending_chapters:
                warnings.append(
                    f"可续扫：已完成 {len(scan_state.completed_chapters)} 章，剩余 {len(pending_chapters)} 章"
                )
            else:
                warnings.append("可续扫：所有章节已完成")
        else:
            diagnosis = ScanStateStore.diagnose_compatibility(
                scan_state,
                config_snapshot=snapshot,
                profile_version=profile_version,
            )
            warnings.append(f"无法续扫：{diagnosis}")
            scan_state = None

    return ScanStartupResult(
        ready=not errors,
        errors=errors,
        warnings=warnings,
        chapter_files=chapter_files,
        selected_chapter_files=selected,
        resumable_state=scan_state,
        pending_chapter_files=pending_chapters,
    )


def build_precise_chapter_batches(
    chapter_files: Sequence[str],
    config: TriggerScanConfig,
) -> List[List[str]]:
    return _batch_items([str(item) for item in chapter_files], config.precise_chapter_batch_size)


BATCH_PREFIX_PATTERN = re.compile(r"^B\d+_")


def build_batched_chapter_prompt(
    chapter_indexes: Sequence[ChapterParagraphIndex],
) -> tuple[str, Dict[str, str]]:
    """Build a combined prompt text for multiple chapters, mapping prefixed paragraph IDs back to originals.

    Returns (combined_text, prefixed_to_original_map).
    """
    parts: List[str] = []
    prefixed_to_original: Dict[str, str] = {}
    for batch_index, chapter_index in enumerate(chapter_indexes):
        prefix = f"B{batch_index}_"
        prefixed_chunks: List[str] = []
        for chunk in chapter_index.chunks:
            prefixed_lines = []
            for line in chunk.text.split("\n"):
                line = line.strip()
                if not line:
                    prefixed_lines.append(line)
                    continue
                match = re.match(r"^(P\d+)\s", line)
                if match:
                    original_id = match.group(1)
                    prefixed_id = f"{prefix}{original_id}"
                    prefixed_to_original[prefixed_id] = original_id
                    prefixed_lines.append(line.replace(original_id, prefixed_id, 1))
                else:
                    prefixed_lines.append(line)
            prefixed_chunks.append("\n".join(prefixed_lines))
        chunk_text = "\n\n".join(prefixed_chunks)
        parts.append(
            f"【章节文件】{chapter_index.chapter_file}\n"
            f"【章节标题】{chapter_index.chapter_title}\n"
            f"【段落文本】\n{chunk_text}"
        )
    return "\n\n".join(parts), prefixed_to_original


def parse_batched_precise_findings(
    model_output: str,
    *,
    chapter_indexes: Sequence[ChapterParagraphIndex],
    prefixed_to_original: Dict[str, str],
    profile: TriggerProfile,
    config: TriggerScanConfig,
) -> List[ScanFinding]:
    """Parse findings from a batched precise scan that covered multiple chapters.

    Paragraph IDs in the findings are expected to be prefixed (e.g., B0_P001).
    The prefix is stripped and findings are assigned to the correct chapter.
    Falls back to looking up unprefixed IDs across all chapters in the batch.
    """
    raw_findings = require_json_list(model_output)
    rules = _rule_lookup(profile)
    index_by_original: Dict[str, ChapterParagraphIndex] = {}
    chapter_files = [chapter_index.chapter_file for chapter_index in chapter_indexes]
    for chapter_index in chapter_indexes:
        for paragraph in chapter_index.paragraphs:
            index_by_original[paragraph.id] = chapter_index
    findings: List[ScanFinding] = []
    for raw_idx, raw in enumerate(raw_findings):
        if not isinstance(raw, dict):
            raise TriggerScanJsonError("finding item must be a JSON object")
        raw = _normalize_raw_finding(raw, config)
        rule_id = str(raw.get("rule_id", "")).strip()
        rule = rules.get(rule_id)
        if rule is None:
            raise TriggerScanJsonError(
                f"unknown rule_id: {rule_id} (finding #{raw_idx}, chapters: {chapter_files})"
            )
        prefixed_ids = [str(item) for item in raw.get("paragraph_ids", [])]
        if not prefixed_ids:
            raise TriggerScanJsonError(
                f"finding contains no paragraph_ids (finding #{raw_idx}, rule: {rule_id})"
            )
        # Resolve prefixed paragraph IDs to originals and group by chapter
        chapter_original_ids: Dict[str, List[str]] = {}
        for prefixed_id in prefixed_ids:
            original = prefixed_to_original.get(prefixed_id)
            if original is None:
                stripped = BATCH_PREFIX_PATTERN.sub("", prefixed_id, count=1)
                original = stripped if stripped in index_by_original else None
            if original is None:
                original = prefixed_id if prefixed_id in index_by_original else None
            if original is None:
                known_prefixes = sorted({k for k in prefixed_to_original if k.startswith("B")}, key=lambda x: x)[:5]
                raise TriggerScanJsonError(
                    f"finding contains unknown paragraph_id: {prefixed_id} "
                    f"(finding #{raw_idx}, rule: {rule_id}, chapters: {chapter_files}, "
                    f"expected prefixes: {known_prefixes})"
                )
            matched_index = index_by_original.get(original)
            if matched_index is None:
                raise TriggerScanJsonError(
                    f"finding contains unknown paragraph_id: {prefixed_id} "
                    f"(finding #{raw_idx}, rule: {rule_id})"
                )
            chapter_original_ids.setdefault(matched_index.chapter_file, []).append(original)

        # Pick the chapter with the most paragraph_ids as the primary chapter
        primary_chapter = max(chapter_original_ids, key=lambda ch: len(chapter_original_ids[ch]))
        chapter_index = index_by_original.get(chapter_original_ids[primary_chapter][0])
        original_ids = [oid for ids in chapter_original_ids.values() for oid in ids]

        finding = ScanFinding.from_dict(
            {
                **raw,
                "finding_id": str(raw.get("finding_id") or f"finding_{uuid.uuid4().hex}"),
                "rule_name": rule.name,
                "chapter_file": chapter_index.chapter_file,
                "chapter_title": chapter_index.chapter_title,
                "paragraph_ids": original_ids,
                "spoiler_levels": raw.get("spoiler_levels", {}),
            }
        )
        finding.to_dict()
        findings.append(finding)
    return apply_finding_filters(findings, profile, config)


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
        str(item.get("finding_id")): item
        for item in verdicts
        if isinstance(item, dict)
    }
    verified: List[ScanFinding] = []
    for finding in findings:
        verdict_item = verdict_by_id.get(finding.finding_id, {})
        verdict = str(verdict_item.get("verdict", "confirmed")).strip()
        reason = str(verdict_item.get("reason", "")).strip()
        if verdict == "false_positive":
            finding.verification_status = "false_positive"
            finding.verification_note = reason
            if retain_false_positives:
                finding.review_status = "false_positive"
                verified.append(finding)
            continue
        finding.review_status = "confirmed"
        finding.verification_status = "confirmed"
        finding.verification_note = reason
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
