from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from logic.article_summary_logic import run_article_summary_process
from logic.chapter_splitter import split_novel_into_chapter_files
from logic.custom_summary_logic import run_custom_summary_process
from logic.llm_api import get_llm_summary_with_config
from logic.orchestrator import run_summarization_process
from logic.paragraph_index import (
    build_chapter_paragraph_index,
    extract_paragraph_context,
)
from logic.trigger_scan import (
    ScanStateStore,
    aggregate_findings_into_events,
    apply_verification_results,
    build_coarse_summary_batches,
    build_precise_chapter_batches,
    build_verification_batches,
    discover_small_summary_coverage,
    merge_adjacent_findings,
    parse_coarse_scan_response,
    parse_precise_scan_findings,
    validate_scan_startup,
)
from logic.trigger_scan.prompts import (
    TRIGGER_AGGREGATION_PROMPT_KEY,
    TRIGGER_COARSE_SCAN_PROMPT_KEY,
    TRIGGER_PRECISE_SCAN_PROMPT_KEY,
    TRIGGER_VERIFICATION_PROMPT_KEY,
    load_trigger_scan_prompt_configs,
    render_trigger_prompt_messages,
)
from logic.trigger_scan.reporting import TriggerScanReportStore
from logic.utils import read_file_content_robustly
from webui_backend.trigger_models import (
    RuleHitSummary,
    ScanFinding,
    ScanReport,
    ScanReportSummary,
    TriggerProfile,
)

from .config_models import (
    ApiConfig,
    ArticleSummaryRequest,
    CustomSummaryRequest,
    NovelSummaryRequest,
    SplitterRequest,
    TriggerScanRequest,
)
from .config_service import resolve_api_config
from .task_runtime import TaskRecord


def select_api_configs(
    configs: Iterable[ApiConfig],
    selected_ids: Iterable[str] | None = None,
) -> List[Dict]:
    selected = set(selected_ids or [])
    active_configs = []
    for config in configs:
        if not config.is_active:
            continue
        if selected and config.id not in selected:
            continue
        resolved = resolve_api_config(config)
        active_configs.append(resolved)
    return active_configs


def find_api_config(configs: Iterable[ApiConfig], api_id: str) -> Dict:
    for config in configs:
        if config.id == api_id:
            return resolve_api_config(config)
    raise ValueError(f"Unknown api_id: {api_id}")


def make_runtime_log_callback(emit: Callable[..., None]):
    def log_callback(*args, **kwargs):
        message = kwargs.get("message")
        if message is None and args:
            message = args[0]
        source_id = (
            kwargs.get("source_id")
            or kwargs.get("api_id_for_log")
            or kwargs.get("api_id")
            or "global"
        )
        emit(
            event_type="log",
            message=str(message or ""),
            source_id=str(source_id),
            status=kwargs.get("status"),
            progress_text=kwargs.get("progress_text"),
        )

    return log_callback


def create_novel_summary_runner(request: NovelSummaryRequest, api_configs: List[Dict]):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)
        ultimate_api_id = request.ultimate_api_id or (api_configs[0]["id"] if api_configs else "")
        success = await run_summarization_process(
            novel_folder_path=request.source_folder_path,
            active_api_configs=api_configs,
            log_callback=log_callback,
            pause_event=pause_signal,
            summary_batch_size=request.summary_batch_size,
            big_summary_batch_size=request.big_summary_batch_size,
            super_summary_threshold=request.super_summary_threshold,
            ultimate_api_id=ultimate_api_id,
            word_counts=request.word_counts.to_dict(),
            use_fine_grained_flow=request.use_fine_grained_flow,
            stop_after_small_summary=request.stop_after_small_summary,
            summary_output_format=request.summary_output_format,
        )
        return "success" if success else "failed"

    return runner


def create_article_summary_runner(request: ArticleSummaryRequest, api_configs: List[Dict]):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)
        success = await run_article_summary_process(
            source_folder_path=request.source_folder_path,
            active_api_configs=api_configs,
            gui_log_callback=log_callback,
            gui_pause_event=pause_signal,
            gui_stop_event=None,
            word_counts=request.word_counts.to_dict(),
            selected_files=request.selected_files,
            output_subfolder=request.output_subfolder,
        )
        return "success" if success else "failed"

    return runner


def create_custom_summary_runner(request: CustomSummaryRequest, api_config: Dict):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)
        result = await run_custom_summary_process(
            selected_file_paths=request.selected_file_paths,
            user_prompt=request.user_prompt,
            api_config=api_config,
            pause_event=pause_signal,
            log_callback=log_callback,
        )
        return str(result)[:200] if result is not None else "failed"

    return runner


def create_splitter_runner(request: SplitterRequest):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)

        def run_sync():
            return split_novel_into_chapter_files(
                source_txt_file_path=request.source_txt_file_path,
                output_directory_path=request.output_directory_path,
                mode=request.mode,
                custom_pattern=request.custom_pattern,
                title_list=request.title_list,
                handle_volumes=request.handle_volumes,
                log_callback=lambda msg, level="INFO", **kwargs: log_callback(
                    message=msg,
                    status=level,
                    **kwargs,
                ),
            )

        success, count = await asyncio.to_thread(run_sync)
        return f"generated {count} files" if success else "failed"

    return runner


COARSE_OUTPUT_SCHEMA = json.dumps(
    {
        "suspected_chapters": ["第001章.txt"],
        "suspected_rule_ids": ["rule_id"],
    },
    ensure_ascii=False,
)
PRECISE_OUTPUT_SCHEMA = json.dumps(
    {
        "findings": [
            {
                "rule_id": "rule_id",
                "severity": 3,
                "confidence": 0.85,
                "paragraph_ids": ["P001"],
                "is_main_plot": True,
                "spoiler_levels": {
                    "low": {"description": "低剧透描述"},
                    "standard": {"description": "标准描述"},
                    "detailed": {
                        "description": "详细描述",
                        "evidence_quote": "原文证据",
                        "skip_advice": "跳读建议",
                    },
                },
            }
        ]
    },
    ensure_ascii=False,
)
VERIFICATION_OUTPUT_SCHEMA = json.dumps(
    {
        "items": [
            {
                "finding_id": "finding_id",
                "verdict": "confirmed",
                "confidence_delta": 0,
                "reason": "复核理由",
            }
        ]
    },
    ensure_ascii=False,
)


def _emit_scan_progress(
    emit: Callable[..., None],
    *,
    stage: str,
    completed: int,
    total: int,
    message: str,
    status: str = "INFO",
    extra: Dict[str, Any] | None = None,
) -> None:
    total = max(int(total or 0), 0)
    completed = max(int(completed or 0), 0)
    progress_text = f"{stage}: {completed}/{total}" if total else stage
    data = {
        "stage": stage,
        "completed": completed,
        "total": total,
        **(extra or {}),
    }
    emit(
        event_type="progress",
        message=message,
        source_id="trigger_scan",
        status=status,
        progress_text=progress_text,
        data=data,
    )


def _enabled_rules_payload(profile: TriggerProfile) -> List[Dict[str, Any]]:
    return [
        rule.to_dict()
        for rule in profile.rules
        if rule.enabled
    ]


def _compact_scan_settings(request: TriggerScanRequest) -> Dict[str, Any]:
    return {
        **request.scan_config.to_dict(),
        "project_slug": request.project_slug,
        "source_folder_path": request.source_folder_path,
    }


def _read_summary_batch_text(summary_files: Iterable[str]) -> str:
    parts = []
    for summary_file in summary_files:
        path = Path(summary_file)
        parts.append(
            f"【{path.name}】\n{read_file_content_robustly(str(path))}"
        )
    return "\n\n".join(parts)


def _chapter_prompt_text(chapter_index) -> str:
    chunk_text = "\n\n".join(chunk.text for chunk in chapter_index.chunks)
    return (
        f"【章节文件】{chapter_index.chapter_file}\n"
        f"【章节标题】{chapter_index.chapter_title}\n"
        f"【段落文本】\n{chunk_text}"
    )


def _context_for_findings(findings: Iterable[ScanFinding], indexes_by_name: Dict[str, Any]) -> str:
    parts = []
    for finding in findings:
        chapter_index = indexes_by_name.get(Path(finding.chapter_file).name)
        if chapter_index is None:
            continue
        context = extract_paragraph_context(chapter_index, finding.paragraph_ids, before=1, after=1)
        parts.append(
            f"【finding_id】{finding.finding_id}\n"
            f"【章节】{finding.chapter_file}\n"
            f"{context.text}"
        )
    return "\n\n".join(parts)


def _build_report_summary(findings: Iterable[ScanFinding]) -> ScanReportSummary:
    finding_list = list(findings)
    hits: Dict[str, RuleHitSummary] = {}
    for finding in finding_list:
        hit = hits.setdefault(
            finding.rule_id,
            RuleHitSummary(rule_id=finding.rule_id, count=0, max_severity=1),
        )
        hit.count += 1
        hit.max_severity = max(hit.max_severity, finding.severity)
    return ScanReportSummary(
        total_findings=len(finding_list),
        verified_findings=len(
            [finding for finding in finding_list if finding.review_status == "confirmed"]
        ),
        pending_review=len(
            [finding for finding in finding_list if finding.review_status == "unreviewed"]
        ),
        rules_hit=sorted(hits.values(), key=lambda item: item.rule_id),
    )


def _api_for_index(api_configs: List[Dict], index: int) -> Dict:
    if not api_configs:
        raise ValueError("At least one scan API config is required")
    return api_configs[index % len(api_configs)]


def _profile_version(profile: TriggerProfile) -> str:
    return str(profile.updated_at or profile.created_at or profile.id)


def create_trigger_scan_runner(
    request: TriggerScanRequest,
    profile: TriggerProfile,
    scan_api_configs: List[Dict],
    verification_api_config: Dict | None = None,
):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)
        config = request.scan_config
        prompt_configs = load_trigger_scan_prompt_configs()
        report_store = TriggerScanReportStore(request.project_output_directory_path)
        state_store = ScanStateStore(request.source_folder_path, record.task_id)
        report = ScanReport(
            report_id=f"report_{record.task_id}",
            project_slug=request.project_slug,
            profile_id=profile.id,
            profile_name=profile.name,
            scan_mode=config.scan_mode,
            scan_range=config.scan_range,
            scan_config=config,
            created_at=time.time(),
            status="running",
            profile_snapshot=profile.to_dict(),
        )
        report_store.save_report(report)
        state_store.create(config.to_dict(), _profile_version(profile))

        rules_json = json.dumps(_enabled_rules_payload(profile), ensure_ascii=False, indent=2)
        scan_settings_json = json.dumps(_compact_scan_settings(request), ensure_ascii=False, indent=2)
        all_findings: List[ScanFinding] = []
        indexes_by_name: Dict[str, Any] = {}

        try:
            startup = validate_scan_startup(
                novel_folder_path=request.source_folder_path,
                profile=profile,
                config=config,
                available_api_ids=[
                    api["id"] for api in scan_api_configs
                ] + ([verification_api_config["id"]] if verification_api_config else []),
                profile_version=_profile_version(profile),
            )
            if not startup.ready:
                raise ValueError("; ".join(startup.errors))

            selected_chapters = startup.selected_chapter_files
            precise_chapters = selected_chapters
            _emit_scan_progress(
                emit,
                stage="precheck",
                completed=1,
                total=1,
                message="扫描预检通过",
                status="SUCCESS",
                extra={"warnings": startup.warnings},
            )

            if config.scan_mode == "hybrid":
                coverage = discover_small_summary_coverage(
                    request.source_folder_path,
                    selected_chapters,
                )
                summary_batches = build_coarse_summary_batches(
                    coverage.summary_files,
                    config,
                )
                suspected_chapter_names: set[str] = set()
                suspected_rule_ids: set[str] = set()
                for batch_index, batch in enumerate(summary_batches):
                    await asyncio.to_thread(pause_signal.wait, 0)
                    variables = {
                        "trigger_rules_json": rules_json,
                        "scan_settings_json": scan_settings_json,
                        "small_summary_batch_text": _read_summary_batch_text(batch),
                        "output_json_schema": COARSE_OUTPUT_SCHEMA,
                    }
                    render_trigger_prompt_messages(
                        TRIGGER_COARSE_SCAN_PROMPT_KEY,
                        prompt_configs[TRIGGER_COARSE_SCAN_PROMPT_KEY],
                        variables,
                    )
                    output = await get_llm_summary_with_config(
                        _api_for_index(scan_api_configs, batch_index),
                        prompt_configs[TRIGGER_COARSE_SCAN_PROMPT_KEY],
                        variables,
                        log_callback,
                        task_info={
                            "novel_folder_path": request.source_folder_path,
                            "stage": "trigger_coarse_scan",
                            "source_files": batch,
                        },
                    )
                    coarse = parse_coarse_scan_response(
                        output,
                        valid_chapter_files=selected_chapters,
                        valid_rule_ids=[rule.id for rule in profile.rules if rule.enabled],
                    )
                    suspected_chapter_names.update(coarse.suspected_chapters)
                    suspected_rule_ids.update(coarse.suspected_rule_ids)
                    _emit_scan_progress(
                        emit,
                        stage="coarse_scan",
                        completed=batch_index + 1,
                        total=len(summary_batches),
                        message="粗筛批次完成",
                        extra={
                            "suspected_chapters": sorted(suspected_chapter_names),
                            "suspected_rule_ids": sorted(suspected_rule_ids),
                        },
                    )
                precise_chapters = [
                    chapter
                    for chapter in selected_chapters
                    if Path(chapter).name in suspected_chapter_names
                ]

            chapter_batches = build_precise_chapter_batches(precise_chapters, config)
            processed_chapters = 0
            for batch_index, batch in enumerate(chapter_batches):
                _emit_scan_progress(
                    emit,
                    stage="precise_scan",
                    completed=processed_chapters,
                    total=len(precise_chapters),
                    message="开始精确扫描批次",
                    extra={"batch_index": batch_index},
                )
                for chapter_path in batch:
                    await asyncio.to_thread(pause_signal.wait, 0)
                    chapter_index = await asyncio.to_thread(
                        build_chapter_paragraph_index,
                        chapter_path,
                        novel_folder_path=request.source_folder_path,
                    )
                    indexes_by_name[chapter_index.chapter_file] = chapter_index
                    variables = {
                        "trigger_rules_json": rules_json,
                        "scan_settings_json": scan_settings_json,
                        "chapter_text_with_paragraph_ids": _chapter_prompt_text(chapter_index),
                        "maximum_quote_length": config.max_quote_chars,
                        "skip_advice_setting": "开启" if config.generate_skip_advice else "关闭",
                        "output_json_schema": PRECISE_OUTPUT_SCHEMA,
                    }
                    render_trigger_prompt_messages(
                        TRIGGER_PRECISE_SCAN_PROMPT_KEY,
                        prompt_configs[TRIGGER_PRECISE_SCAN_PROMPT_KEY],
                        variables,
                    )
                    output = await get_llm_summary_with_config(
                        _api_for_index(scan_api_configs, processed_chapters),
                        prompt_configs[TRIGGER_PRECISE_SCAN_PROMPT_KEY],
                        variables,
                        log_callback,
                        task_info={
                            "novel_folder_path": request.source_folder_path,
                            "stage": "trigger_precise_scan",
                            "source_file": chapter_path,
                        },
                    )
                    findings = parse_precise_scan_findings(
                        output,
                        chapter_index=chapter_index,
                        profile=profile,
                        config=config,
                    )
                    all_findings.extend(findings)
                    for finding in findings:
                        emit(
                            event_type="finding",
                            message=f"发现疑似雷点：{finding.rule_name}",
                            source_id="trigger_scan",
                            status="INFO",
                            data={"finding": finding.to_dict()},
                        )
                    state_store.mark_chapter_complete(chapter_path)
                    processed_chapters += 1
                    _emit_scan_progress(
                        emit,
                        stage="precise_scan",
                        completed=processed_chapters,
                        total=len(precise_chapters),
                        message="章节精确扫描完成",
                        extra={"chapter_file": Path(chapter_path).name},
                    )

            if config.verification_enabled and all_findings:
                verification_batches = build_verification_batches(all_findings, config)
                verifier = verification_api_config or _api_for_index(scan_api_configs, 0)
                verified_findings = list(all_findings)
                for batch_index, batch in enumerate(verification_batches):
                    await asyncio.to_thread(pause_signal.wait, 0)
                    variables = {
                        "trigger_rules_json": rules_json,
                        "referenced_paragraph_context": _context_for_findings(batch, indexes_by_name),
                        "first_pass_findings_json": json.dumps(
                            [finding.to_dict() for finding in batch],
                            ensure_ascii=False,
                            indent=2,
                        ),
                        "output_json_schema": VERIFICATION_OUTPUT_SCHEMA,
                    }
                    render_trigger_prompt_messages(
                        TRIGGER_VERIFICATION_PROMPT_KEY,
                        prompt_configs[TRIGGER_VERIFICATION_PROMPT_KEY],
                        variables,
                    )
                    output = await get_llm_summary_with_config(
                        verifier,
                        prompt_configs[TRIGGER_VERIFICATION_PROMPT_KEY],
                        variables,
                        log_callback,
                        task_info={
                            "novel_folder_path": request.source_folder_path,
                            "stage": "trigger_verification",
                        },
                    )
                    verified_batch = apply_verification_results(batch, output)
                    verified_ids = {finding.finding_id for finding in verified_batch}
                    verified_findings = [
                        finding
                        for finding in verified_findings
                        if finding not in batch or finding.finding_id in verified_ids
                    ]
                    _emit_scan_progress(
                        emit,
                        stage="verification",
                        completed=batch_index + 1,
                        total=len(verification_batches),
                        message="二次验证批次完成",
                    )
                all_findings = verified_findings

            _emit_scan_progress(
                emit,
                stage="aggregation",
                completed=0,
                total=1,
                message="开始聚合雷点事件",
            )
            render_trigger_prompt_messages(
                TRIGGER_AGGREGATION_PROMPT_KEY,
                prompt_configs[TRIGGER_AGGREGATION_PROMPT_KEY],
                {
                    "findings_json": json.dumps(
                        [finding.to_dict() for finding in all_findings],
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "scan_settings_json": scan_settings_json,
                    "output_json_schema": "{}",
                },
            )
            merged_findings = merge_adjacent_findings(all_findings)
            report.findings = merged_findings
            report.events = aggregate_findings_into_events(merged_findings)
            report.summary = _build_report_summary(merged_findings)
            report.status = "completed"
            report.completed_at = time.time()
            report_store.save_report(report)
            _emit_scan_progress(
                emit,
                stage="reporting",
                completed=1,
                total=1,
                message="扫描报告已保存",
                status="SUCCESS",
                extra={"report_id": report.report_id},
            )
            emit(
                event_type="report",
                message="扫描报告已完成",
                source_id="trigger_scan",
                status="SUCCESS",
                data={"report_id": report.report_id, "summary": report.summary.to_dict()},
            )
            return f"report:{report.report_id}"
        except asyncio.CancelledError:
            report.status = "cancelled"
            report_store.save_partial_report(report, status="cancelled")
            raise
        except Exception:
            report.status = "failed"
            report.findings = all_findings
            report.summary = _build_report_summary(all_findings)
            report_store.save_partial_report(report, status="failed")
            raise

    return runner
