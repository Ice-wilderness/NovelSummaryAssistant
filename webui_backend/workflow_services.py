from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from logic.article_summary_logic import run_article_summary_process
from logic.chapter_boundaries import ChapterSplitError
from logic.chapter_splitter import split_novel_into_chapter_files
from logic.custom_summary_logic import run_custom_summary_process
from logic.llm_api import GENERAL_RETRY_DELAYS, get_llm_summary_with_config
from logic.utils import check_pause_async, log_api_failure_to_file, natural_sort_key
from logic.orchestrator import run_summarization_process
from logic.paragraph_index import (
    build_chapter_paragraph_index,
    extract_paragraph_context,
)
from logic.trigger_scan import (
    ScanStateStore,
    aggregate_findings_into_events,
    apply_verification_results,
    build_batched_chapter_prompt,
    build_precise_chapter_batches,
    build_verification_batches,
    merge_adjacent_findings,
    parse_batched_precise_findings,
    parse_precise_scan_findings,
    validate_scan_startup,
)
from logic.trigger_scan.prompts import (
    TRIGGER_PRECISE_SCAN_PROMPT_KEY,
    TRIGGER_VERIFICATION_PROMPT_KEY,
    load_trigger_scan_prompt_configs,
    render_trigger_prompt_messages,
)
from logic.trigger_scan.reporting import TriggerScanReportStore
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
from .task_runtime import TaskRecord, TaskRunOutcome


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


def _summary_result_to_outcome(result: Any) -> TaskRunOutcome | str:
    if hasattr(result, "status"):
        return TaskRunOutcome(
            status=str(getattr(result, "status")),
            result_summary=str(getattr(result, "result_summary", "") or ""),
            error=getattr(result, "error", None),
            warnings=list(getattr(result, "warnings", []) or []),
            data=dict(getattr(result, "data", {}) or {}),
        )
    return "success" if result else "failed"


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
            progress_emitter=emit,
        )
        return "success" if success else "failed"

    return runner


def create_article_summary_runner(request: ArticleSummaryRequest, api_configs: List[Dict]):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)
        result = await run_article_summary_process(
            source_folder_path=request.source_folder_path,
            active_api_configs=api_configs,
            gui_log_callback=log_callback,
            gui_pause_event=pause_signal,
            gui_stop_event=None,
            word_counts=request.word_counts.to_dict(),
            selected_files=request.selected_files,
            output_subfolder=request.output_subfolder,
        )
        return _summary_result_to_outcome(result)

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
        if hasattr(result, "status"):
            return _summary_result_to_outcome(result)
        return str(result)[:200] if result is not None else "failed"

    return runner


def create_splitter_runner(request: SplitterRequest):
    async def runner(record: TaskRecord, pause_signal, emit):
        log_callback = make_runtime_log_callback(emit)

        # 解析 pattern_config_id
        custom_pattern = request.custom_pattern
        pattern_config = None
        if request.mode == "regex" and request.pattern_config_id:
            from webui_backend.pattern_config_service import PatternConfigService
            from .file_services import get_runtime_base_path
            config_path = get_runtime_base_path() / "chapter_patterns.json"
            svc = PatternConfigService(config_path)
            try:
                pattern_config = svc.get(request.pattern_config_id)
                if pattern_config.regex_mode == "simple":
                    custom_pattern = pattern_config.pattern
                # raw 模式通过 pattern_config 参数传递
            except ValueError:
                pass

        def run_sync():
            return split_novel_into_chapter_files(
                source_txt_file_path=request.source_txt_file_path,
                output_directory_path=request.output_directory_path,
                mode=request.mode,
                custom_pattern=custom_pattern,
                title_list=request.title_list,
                handle_volumes=request.handle_volumes,
                pattern_config=pattern_config,
                raise_on_error=True,
                log_callback=lambda msg, level="INFO", **kwargs: log_callback(
                    message=msg,
                    status=level,
                    **kwargs,
                ),
            )

        try:
            success, count = await asyncio.to_thread(run_sync)
        except ChapterSplitError as exc:
            detail = f"{exc.message} {exc.hint}".strip()
            return TaskRunOutcome(status="failed", result_summary="failed", error=detail)
        return f"generated {count} files" if success else "failed"

    return runner


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
    stages: List[Dict[str, Any]] | None = None,
    current_stage: str = "",
) -> None:
    total = max(int(total or 0), 0)
    completed = max(int(completed or 0), 0)
    progress_text = f"{stage}: {completed}/{total}" if total else stage
    data: Dict[str, Any] = {
        "stage": stage,
        "completed": completed,
        "total": total,
        **(extra or {}),
    }
    if stages is not None:
        data["stages"] = [dict(stage) for stage in stages]
    if current_stage:
        data["current_stage"] = current_stage
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


def _chapter_prompt_text(chapter_index) -> str:
    chunk_text = "\n\n".join(chunk.text for chunk in chapter_index.chunks)
    return (
        f"【章节文件】{chapter_index.chapter_file}\n"
        f"【章节标题】{chapter_index.chapter_title}\n"
        f"【段落文本】\n{chunk_text}"
    )


def _chapter_index_for_finding(finding: ScanFinding, indexes_by_name: Dict[str, Any]):
    return (
        indexes_by_name.get(Path(finding.chapter_file).name)
        or indexes_by_name.get(finding.chapter_file)
    )


def _context_for_findings(findings: Iterable[ScanFinding], indexes_by_name: Dict[str, Any]) -> str:
    parts = []
    for finding in findings:
        chapter_index = _chapter_index_for_finding(finding, indexes_by_name)
        if chapter_index is None:
            continue
        context = extract_paragraph_context(chapter_index, finding.paragraph_ids, before=1, after=1)
        parts.append(
            f"【finding_id】{finding.finding_id}\n"
            f"【章节】{finding.chapter_file}\n"
            f"{context.text}"
        )
    return "\n\n".join(parts)


def _has_verification_context(finding: ScanFinding, indexes_by_name: Dict[str, Any]) -> bool:
    chapter_index = _chapter_index_for_finding(finding, indexes_by_name)
    if chapter_index is None:
        return False
    context = extract_paragraph_context(chapter_index, finding.paragraph_ids, before=1, after=1)
    return bool(context.matched_paragraph_ids) and not context.missing_paragraph_ids


def _requires_verification(finding: ScanFinding) -> bool:
    if finding.source_kind == "historical_report":
        return finding.verification_status in {"unknown", "pending"}
    return finding.source_kind in {"current_run", "unknown"}


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

        if request.resume_from_report_id:
            # Continue an existing report
            report = report_store.load_report(request.resume_from_report_id)
            report.status = "running"
            report.scan_config = config
            report.profile_snapshot = profile.to_dict()
            report.completed_at = None
            report_store.save_report(report)
        else:
            # Create a fresh report
            report = ScanReport(
                report_id=f"report_{record.task_id}",
                project_slug=request.project_slug,
                profile_id=profile.id,
                profile_name=profile.name,
                scan_mode="precise",
                scan_range=config.scan_range,
                scan_config=config,
                created_at=time.time(),
                status="running",
                profile_snapshot=profile.to_dict(),
            )
            report_store.save_report(report)

        async def _write_scan_failure_log(stage: str, raw_output: str, error_msg: str, extra: Dict[str, Any] | None = None) -> None:
            try:
                await log_api_failure_to_file(
                    request.source_folder_path,
                    "trigger_scan",
                    {
                        "timestamp": time.time(),
                        "stage": stage,
                        "error": error_msg,
                        "raw_output": raw_output,
                        "raw_output_length": len(raw_output),
                        **(extra or {}),
                    },
                )
            except Exception:
                pass

        rules_json = json.dumps(_enabled_rules_payload(profile), ensure_ascii=False, indent=2)
        scan_settings_json = json.dumps(_compact_scan_settings(request), ensure_ascii=False, indent=2)
        # Preserve existing findings when resuming
        all_findings: List[ScanFinding] = list(report.findings) if request.resume_from_report_id else []
        historical_task_id = (
            request.resume_from_report_id.removeprefix("report_")
            if request.resume_from_report_id.startswith("report_")
            else ""
        )
        for finding in all_findings:
            if not finding.source_report_id:
                finding.source_report_id = request.resume_from_report_id
            if not finding.source_task_id:
                finding.source_task_id = historical_task_id
            if finding.source_kind == "unknown":
                finding.source_kind = "historical_report"
        indexes_by_name: Dict[str, Any] = {}
        selected_chapters_for_report: List[str] = []
        current_scan_stage = "startup"

        def _resolve_chapter_path(chapter_file: str) -> Path | None:
            path = Path(chapter_file)
            if path.is_file():
                return path
            candidate = Path(request.source_folder_path) / path.name
            if candidate.is_file():
                return candidate
            return None

        async def _ensure_verification_indexes(findings: Iterable[ScanFinding]) -> None:
            for finding in findings:
                if _chapter_index_for_finding(finding, indexes_by_name) is not None:
                    continue
                chapter_path = _resolve_chapter_path(finding.chapter_file)
                if chapter_path is None:
                    continue
                try:
                    chapter_index = await asyncio.to_thread(
                        build_chapter_paragraph_index,
                        chapter_path,
                        novel_folder_path=request.source_folder_path,
                    )
                except OSError:
                    continue
                indexes_by_name[chapter_index.chapter_file] = chapter_index

        def _mark_unverified(finding: ScanFinding, note: str) -> None:
            finding.verification_status = "unverified"
            finding.verification_note = note
            warning = (
                f"unverified finding {finding.finding_id} in "
                f"{Path(finding.chapter_file).name}: {note}"
            )
            if warning not in report.warnings:
                report.warnings.append(warning)

        try:
            # When resuming, use the original report's config snapshot for compatibility
            resume_snapshot = report.scan_config.to_dict() if request.resume_from_report_id else None
            startup = validate_scan_startup(
                novel_folder_path=request.source_folder_path,
                profile=profile,
                config=config,
                available_api_ids=[
                    api["id"] for api in scan_api_configs
                ] + ([verification_api_config["id"]] if verification_api_config else []),
                profile_version=_profile_version(profile),
                resume_from_report_id=request.resume_from_report_id,
                config_snapshot=resume_snapshot,
            )
            if not startup.ready:
                raise ValueError("; ".join(startup.errors))

            # Resume: use pending chapters, keep completed from previous state
            selected_chapters = list(startup.selected_chapter_files)
            selected_chapters_for_report = selected_chapters
            precise_chapters = startup.pending_chapter_files
            selected_total = len(selected_chapters)
            pending_total = len(precise_chapters)
            completed_from_resume = 0
            if startup.resumable_state is not None:
                selected_chapter_set = set(selected_chapters)
                completed_from_previous = [
                    chapter
                    for chapter in startup.resumable_state.completed_chapters
                    if not selected_chapter_set or chapter in selected_chapter_set
                ]
                completed_from_resume = len(completed_from_previous)
                state_store = ScanStateStore(request.source_folder_path, startup.resumable_state.task_id)
                existing_state = state_store.load()
                if existing_state is not None:
                    state_store.create(config.to_dict(), _profile_version(profile))
                    # restore completed chapters from previous run
                    for ch in completed_from_previous:
                        state_store.mark_chapter_complete(ch)
            else:
                state_store.create(config.to_dict(), _profile_version(profile))

            # Build scan stages for progress bar
            scan_stages = [
                {"id": "precheck", "label": "预检查", "completed": 1, "total": 1, "status": "completed"},
                {"id": "precise_scan", "label": "精确扫描", "completed": completed_from_resume, "total": selected_total, "status": "running"},
            ]
            if config.verification_enabled:
                scan_stages.append({"id": "verification", "label": "验证", "completed": 0, "total": 0, "status": "pending"})
            scan_stages.extend([
                {"id": "aggregation", "label": "聚合", "completed": 0, "total": 1, "status": "pending"},
                {"id": "reporting", "label": "报告", "completed": 0, "total": 1, "status": "pending"},
            ])
            current_scan_stage = "precise_scan"

            def _update_scan_stage(stage_id: str):
                nonlocal current_scan_stage
                found = False
                for s in scan_stages:
                    if s["id"] == stage_id:
                        s["status"] = "running"
                        current_scan_stage = stage_id
                        found = True
                    elif not found:
                        s["status"] = "completed"
                    else:
                        s["status"] = "pending"

            _emit_scan_progress(
                emit,
                stage="precheck",
                completed=1,
                total=1,
                message="扫描预检通过",
                status="SUCCESS",
                extra={
                    "warnings": startup.warnings,
                    "total_chapters": selected_total,
                    "selected_total": selected_total,
                    "completed_from_resume": completed_from_resume,
                    "pending_total": pending_total,
                    "processed_current_run": 0,
                },
                stages=scan_stages,
                current_stage="precise_scan",
            )

            chapter_batches = build_precise_chapter_batches(precise_chapters, config)
            processed_current_run = 0
            async def _process_batch(batch: List[str], batch_index: int, api_config: Dict) -> List[ScanFinding]:
                """Process one batch of chapters with the given API config."""
                batch_indexes_local = []
                for chapter_path in batch:
                    await check_pause_async(pause_signal)
                    chapter_index = await asyncio.to_thread(
                        build_chapter_paragraph_index,
                        chapter_path,
                        novel_folder_path=request.source_folder_path,
                    )
                    batch_indexes_local.append(chapter_index)
                    indexes_by_name[chapter_index.chapter_file] = chapter_index

                batched_text, prefixed_map = build_batched_chapter_prompt(batch_indexes_local)
                variables_local = {
                    "trigger_rules_json": rules_json,
                    "scan_settings_json": scan_settings_json,
                    "chapter_text_with_paragraph_ids": batched_text,
                    "maximum_quote_length": config.max_quote_chars,
                    "skip_advice_setting": "开启" if config.generate_skip_advice else "关闭",
                    "output_json_schema": PRECISE_OUTPUT_SCHEMA,
                }
                render_trigger_prompt_messages(
                    TRIGGER_PRECISE_SCAN_PROMPT_KEY,
                    prompt_configs[TRIGGER_PRECISE_SCAN_PROMPT_KEY],
                    variables_local,
                )
                max_retries = max(0, int(api_config.get("max_retries", 3)))
                for retry in range(max_retries + 1):
                    output = await get_llm_summary_with_config(
                        api_config,
                        prompt_configs[TRIGGER_PRECISE_SCAN_PROMPT_KEY],
                        variables_local,
                        log_callback,
                        task_info={
                            "novel_folder_path": request.source_folder_path,
                            "stage": "trigger_precise_scan",
                            "source_file": f"batch_{batch_index}",
                        },
                    )
                    try:
                        result = parse_batched_precise_findings(
                            output,
                            chapter_indexes=batch_indexes_local,
                            prefixed_to_original=prefixed_map,
                            profile=profile,
                            config=config,
                        )
                        for finding in result:
                            finding.source_report_id = report.report_id
                            finding.source_task_id = record.task_id
                            finding.source_kind = "current_run"
                        return result
                    except Exception as parse_error:
                        await _write_scan_failure_log(
                            "trigger_precise_scan",
                            output,
                            str(parse_error),
                            extra={
                                "batch_index": batch_index,
                                "chapter_files": [idx.chapter_file for idx in batch_indexes_local],
                                "retry": retry,
                            },
                        )
                        if retry < max_retries:
                            delay = GENERAL_RETRY_DELAYS[min(retry, len(GENERAL_RETRY_DELAYS) - 1)]
                            log_callback(
                                message=f"解析失败（{parse_error}），{delay}秒后第{retry + 1}次重试...",
                                source_id="trigger_scan",
                                status="WARN",
                            )
                            await asyncio.sleep(delay)
                        else:
                            raise
                return []  # unreachable

            # Worker pool: one worker per API, pulling from shared queue
            queue: asyncio.Queue = asyncio.Queue()
            for i, batch in enumerate(chapter_batches):
                queue.put_nowait((i, batch))
            results_by_index: Dict[int, List[ScanFinding]] = {}
            processed_lock = asyncio.Lock()

            async def _save_incremental():
                async with processed_lock:
                    report.findings = all_findings
                    report.events = aggregate_findings_into_events(all_findings)
                    report.summary = _build_report_summary(all_findings)
                    report_store.save_report(report)

            async def worker(api_config: Dict):
                nonlocal processed_current_run
                while True:
                    try:
                        bi, batch = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return
                    findings = await _process_batch(batch, bi, api_config)
                    results_by_index[bi] = findings
                    for finding in findings:
                        emit(
                            event_type="finding",
                            message=f"发现疑似雷点：{finding.rule_name}",
                            source_id="trigger_scan",
                            status="INFO",
                            data={"finding": finding.to_dict()},
                        )
                    async with processed_lock:
                        for chapter_path in batch:
                            state_store.mark_chapter_complete(chapter_path)
                        processed_current_run += len(batch)
                        all_findings.extend(findings)
                        all_findings.sort(key=lambda f: (natural_sort_key(f.chapter_file), f.rule_id))
                    await _save_incremental()
                    cumulative_completed = completed_from_resume + processed_current_run
                    scan_stages[1]["completed"] = cumulative_completed
                    _emit_scan_progress(
                        emit,
                        stage="precise_scan",
                        completed=cumulative_completed,
                        total=selected_total,
                        message=f"精确扫描已完成 {cumulative_completed}/{selected_total} 章",
                        extra={
                            "selected_total": selected_total,
                            "completed_from_resume": completed_from_resume,
                            "pending_total": pending_total,
                            "processed_current_run": processed_current_run,
                        },
                        stages=scan_stages,
                        current_stage="precise_scan",
                    )

            _emit_scan_progress(
                emit,
                stage="precise_scan",
                completed=completed_from_resume,
                total=selected_total,
                message=f"并发扫描启动（{len(scan_api_configs)} 个 API 并行）",
                extra={
                    "workers": len(scan_api_configs),
                    "batches": len(chapter_batches),
                    "selected_total": selected_total,
                    "completed_from_resume": completed_from_resume,
                    "pending_total": pending_total,
                    "processed_current_run": 0,
                },
                stages=scan_stages,
                current_stage="precise_scan",
            )
            workers = [
                worker(_api_for_index(scan_api_configs, i))
                for i in range(len(scan_api_configs))
            ]
            await asyncio.gather(*workers)

            if config.verification_enabled and all_findings:
                verification_candidates = [
                    finding for finding in all_findings if _requires_verification(finding)
                ]
                await _ensure_verification_indexes(verification_candidates)
                verifiable_findings: List[ScanFinding] = []
                for finding in verification_candidates:
                    if _has_verification_context(finding, indexes_by_name):
                        finding.verification_status = "pending"
                        verifiable_findings.append(finding)
                    else:
                        _mark_unverified(
                            finding,
                            "无法重建章节段落上下文，未执行二次验证。",
                        )
                verification_batches = build_verification_batches(verifiable_findings, config)
                verifier = verification_api_config or _api_for_index(scan_api_configs, 0)
                verified_findings = list(all_findings)
                # Update stages for verification
                for s in scan_stages:
                    if s["id"] == "verification":
                        s["total"] = len(verification_batches)
                        s["status"] = "running"
                current_scan_stage = "verification"
                for batch_index, batch in enumerate(verification_batches):
                    await check_pause_async(pause_signal)
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
                    verify_max_retries = max(0, int(verifier.get("max_retries", 3)))
                    for retry in range(verify_max_retries + 1):
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
                        try:
                            verified_batch = apply_verification_results(batch, output)
                            break
                        except Exception as parse_error:
                            finding_ids = [f.finding_id for f in batch]
                            await _write_scan_failure_log(
                                "trigger_verification",
                                output,
                                str(parse_error),
                                extra={
                                    "batch_index": batch_index,
                                    "finding_ids": finding_ids[:10],
                                    "retry": retry,
                                },
                            )
                            if retry < verify_max_retries:
                                delay = GENERAL_RETRY_DELAYS[min(retry, len(GENERAL_RETRY_DELAYS) - 1)]
                                log_callback(
                                    message=f"验证解析失败（{parse_error}），{delay}秒后第{retry + 1}次重试...",
                                    source_id="trigger_scan",
                                    status="WARN",
                                )
                                await asyncio.sleep(delay)
                            else:
                                raise
                    verified_ids = {finding.finding_id for finding in verified_batch}
                    verified_findings = [
                        finding
                        for finding in verified_findings
                        if finding not in batch or finding.finding_id in verified_ids
                    ]
                    for s in scan_stages:
                        if s["id"] == "verification":
                            s["completed"] = batch_index + 1
                    _emit_scan_progress(
                        emit,
                        stage="verification",
                        completed=batch_index + 1,
                        total=len(verification_batches),
                        message="二次验证批次完成",
                        stages=scan_stages,
                        current_stage="verification",
                    )
                all_findings = verified_findings

            _update_scan_stage("aggregation")
            _emit_scan_progress(
                emit,
                stage="aggregation",
                completed=0,
                total=1,
                message="开始聚合雷点事件",
                stages=scan_stages,
                current_stage="aggregation",
            )
            merged_findings = merge_adjacent_findings(all_findings)
            report.findings = merged_findings
            report.events = aggregate_findings_into_events(merged_findings)
            report.summary = _build_report_summary(merged_findings)
            report.unscanned_chapters = []
            report.failed_stage = ""
            report.status = "completed"
            report.completed_at = time.time()
            report_store.save_report(report)
            # Clean up scan state since scan completed successfully
            try:
                state_path = state_store.path
                if state_path.exists():
                    state_path.unlink()
            except OSError:
                pass
            _update_scan_stage("reporting")
            for s in scan_stages:
                if s["id"] == "aggregation":
                    s["completed"] = 1
                if s["id"] == "reporting":
                    s["completed"] = 1
            _emit_scan_progress(
                emit,
                stage="reporting",
                completed=1,
                total=1,
                message="扫描报告已保存",
                status="SUCCESS",
                extra={"report_id": report.report_id},
                stages=scan_stages,
                current_stage="reporting",
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
            report.findings = all_findings
            report.summary = _build_report_summary(all_findings)
            completed_chapters = set()
            saved_state = state_store.load()
            if saved_state is not None:
                completed_chapters = set(saved_state.completed_chapters)
            selected_chapter_set = set(selected_chapters_for_report)
            completed_selected = completed_chapters & selected_chapter_set
            unscanned = [
                chapter
                for chapter in selected_chapters_for_report
                if chapter not in completed_chapters
            ]
            report.unscanned_chapters = [Path(chapter).name for chapter in unscanned]
            report.failed_stage = current_scan_stage or "startup"
            has_partial_scan_data = bool(completed_selected) or bool(report.findings)
            if selected_chapters_for_report and (has_partial_scan_data or not unscanned):
                report.status = "partial_failed"
            else:
                report.status = "failed"
            if report.status == "partial_failed":
                warning = f"partial_failed at {report.failed_stage}"
                if report.unscanned_chapters:
                    warning = f"{warning}; unscanned chapters: {', '.join(report.unscanned_chapters)}"
                if warning not in report.warnings:
                    report.warnings.append(warning)
            report_store.save_partial_report(report, status=report.status)
            raise

    return runner
