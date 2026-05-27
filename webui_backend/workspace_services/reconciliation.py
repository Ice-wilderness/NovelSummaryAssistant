from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from logic.prompts import (
    USER_FACING_BIG_CHAR_SUBDIR,
    USER_FACING_BIG_PLOT_SUBDIR,
    USER_FACING_SMALL_CHAR_SUBDIR,
    USER_FACING_SMALL_PLOT_SUBDIR,
    USER_FACING_SUPER_CHAR_P1_SUBDIR,
    USER_FACING_SUPER_CHAR_P2_SUBDIR,
    USER_FACING_SUPER_PLOT_P1_SUBDIR,
    USER_FACING_SUPER_PLOT_P2_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P1_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P2_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P1_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P2_SUBDIR,
)

from .low_state import count_text_files, summary_file_paths
from .progress import count_small_summary_covered_chapters, scan_project_progress


RECONCILIATION_OK = "ok"
RECONCILIATION_INCOMPLETE = "incomplete"
RECONCILIATION_ABNORMAL_COMPLETED = "abnormal_completed"
RECONCILIATION_STATE_INCOMPLETE = "state_incomplete"
RECONCILIATION_UNSUPPORTED = "unsupported"

REPAIR_ACTION_AVAILABLE = "available"
REPAIR_ACTION_BLOCKED = "blocked"

REPAIR_KIND_METADATA = "metadata_reconcile"
REPAIR_KIND_SUMMARY_CONTENT = "summary_content_regeneration"
REPAIR_KIND_UNSUPPORTED = "unsupported"

SUMMARY_TERMINAL_STATUSES = {"success", "partial_failed"}
SUMMARY_OUTPUT_SUBDIRS = [
    USER_FACING_SMALL_PLOT_SUBDIR,
    USER_FACING_SMALL_CHAR_SUBDIR,
    USER_FACING_BIG_PLOT_SUBDIR,
    USER_FACING_BIG_CHAR_SUBDIR,
    USER_FACING_SUPER_PLOT_P1_SUBDIR,
    USER_FACING_SUPER_PLOT_P2_SUBDIR,
    USER_FACING_SUPER_CHAR_P1_SUBDIR,
    USER_FACING_SUPER_CHAR_P2_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P1_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P2_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P1_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P2_SUBDIR,
]
ULTIMATE_CHECKS = [
    ("ultimate_summary_plot_p1", USER_FACING_ULTIMATE_PLOT_P1_SUBDIR, "终极剧情总结 P1"),
    ("ultimate_summary_plot_p2", USER_FACING_ULTIMATE_PLOT_P2_SUBDIR, "终极剧情总结 P2"),
    ("ultimate_summary_char_p1", USER_FACING_ULTIMATE_CHAR_P1_SUBDIR, "终极角色总结 P1"),
    ("ultimate_summary_char_p2", USER_FACING_ULTIMATE_CHAR_P2_SUBDIR, "终极角色总结 P2"),
]


@dataclass
class ReconciliationWarning:
    code: str
    message: str
    severity: str = "warning"
    paths: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "paths": list(self.paths),
        }


@dataclass
class OutputCheck:
    id: str
    label: str
    status: str
    expected: str = ""
    actual: str = ""
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "status": self.status,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
        }


@dataclass
class RepairAction:
    action_id: str
    label: str
    description: str
    status: str = REPAIR_ACTION_AVAILABLE
    blocked_reason: str = ""
    required_inputs: List[str] = field(default_factory=list)
    affected_outputs: List[str] = field(default_factory=list)
    repair_kind: str = REPAIR_KIND_METADATA
    requires_llm: bool = False
    may_overwrite: bool = False
    may_change_content: bool = False
    estimated_scope: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "label": self.label,
            "description": self.description,
            "status": self.status,
            "blocked_reason": self.blocked_reason,
            "required_inputs": list(self.required_inputs),
            "affected_outputs": list(self.affected_outputs),
            "repair_kind": self.repair_kind,
            "requires_llm": self.requires_llm,
            "may_overwrite": self.may_overwrite,
            "may_change_content": self.may_change_content,
            "estimated_scope": self.estimated_scope,
        }


@dataclass
class RepairPlan:
    project_slug: str
    status: str
    actions: List[RepairAction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_slug": self.project_slug,
            "status": self.status,
            "actions": [action.to_dict() for action in self.actions],
        }


@dataclass
class ProjectReconciliation:
    status: str
    warnings: List[ReconciliationWarning] = field(default_factory=list)
    output_checks: List[OutputCheck] = field(default_factory=list)
    repair_plan: Optional[RepairPlan] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reconciliation_status": self.status,
            "reconciliation_warnings": [warning.to_dict() for warning in self.warnings],
            "output_checks": [check.to_dict() for check in self.output_checks],
            "repair_plan": self.repair_plan.to_dict() if self.repair_plan else None,
        }


def warning_messages(warnings: Iterable[ReconciliationWarning | Mapping[str, Any]]) -> List[str]:
    messages: List[str] = []
    for warning in warnings:
        message = (
            warning.message
            if isinstance(warning, ReconciliationWarning)
            else str(warning.get("message", ""))
        )
        if message and message not in messages:
            messages.append(message)
    return messages


class ProjectReconciliationService:
    def reconcile(
        self,
        metadata: Any,
        *,
        latest_task: Mapping[str, Any] | None = None,
        include_repair_plan: bool = True,
    ) -> ProjectReconciliation:
        root = Path(metadata.custom_output_directory or metadata.default_output_directory)
        if metadata.workflow_type == "novel_summary":
            return self._reconcile_novel(metadata, root, latest_task, include_repair_plan)
        return self._reconcile_generic(metadata, root, latest_task, include_repair_plan)

    def repair_metadata(self, metadata: Any) -> ProjectReconciliation:
        root = Path(metadata.custom_output_directory or metadata.default_output_directory)
        metadata.progress = scan_project_progress(metadata.workflow_type, root, metadata.latest_task_status)
        return self.reconcile(metadata, include_repair_plan=True)

    def _reconcile_novel(
        self,
        metadata: Any,
        root: Path,
        latest_task: Mapping[str, Any] | None,
        include_repair_plan: bool,
    ) -> ProjectReconciliation:
        warnings: List[ReconciliationWarning] = []
        output_checks: List[OutputCheck] = []
        progress = metadata.progress or scan_project_progress(metadata.workflow_type, root, metadata.latest_task_status)
        latest_status = _latest_status(metadata, latest_task)
        latest_task_type = _latest_task_type(latest_task)
        states = _load_state_files(root / ".summarizer_cache", warnings)
        state_claims = _state_claims(states)
        chapter_count = count_text_files(root)
        has_outputs = _has_summary_outputs(root)

        if state_claims:
            output_checks.extend(_checks_for_state_claims(root, state_claims, metadata.summary_output_format))

        expects_small_only = latest_task_type == "small_summary_preparation" or _latest_params(latest_task).get("stop_after_small_summary") is True
        latest_summary_completion_claimed = (
            latest_status in SUMMARY_TERMINAL_STATUSES
            and latest_task_type in {"", "novel_summary", "small_summary_preparation"}
        )
        completion_claimed = latest_summary_completion_claimed or bool(state_claims)
        if latest_summary_completion_claimed and not expects_small_only:
            output_checks.extend(_checks_for_ultimate_outputs(root, metadata.summary_output_format))
        elif latest_summary_completion_claimed and expects_small_only:
            output_checks.append(_check_small_summary_coverage(root, chapter_count))

        missing_checks = [check for check in output_checks if check.status in {"missing", "format_mismatch"}]
        if missing_checks and completion_claimed:
            for check in missing_checks:
                warnings.append(
                    ReconciliationWarning(
                        code="missing_output",
                        message=f"{check.label}缺失或格式不一致：{check.message or check.expected}",
                        paths=[check.expected] if check.expected else [],
                    )
                )
            status = RECONCILIATION_ABNORMAL_COMPLETED
        elif completion_claimed:
            status = RECONCILIATION_OK
        elif has_outputs:
            status = RECONCILIATION_STATE_INCOMPLETE
            warnings.append(
                ReconciliationWarning(
                    code="state_metadata_incomplete",
                    message="检测到已有总结产物，但缺少可靠的完成状态记录，请检查项目状态或执行状态校正。",
                )
            )
        elif int(progress.get("percent") or 0) >= 100:
            status = RECONCILIATION_STATE_INCOMPLETE
            warnings.append(
                ReconciliationWarning(
                    code="state_metadata_incomplete",
                    message="项目进度显示完成，但缺少可靠的任务或状态记录。",
                )
            )
        else:
            status = RECONCILIATION_INCOMPLETE

        plan = self._repair_plan(metadata, root, status, warnings, output_checks) if include_repair_plan else None
        return ProjectReconciliation(status=status, warnings=warnings, output_checks=output_checks, repair_plan=plan)

    def _reconcile_generic(
        self,
        metadata: Any,
        root: Path,
        latest_task: Mapping[str, Any] | None,
        include_repair_plan: bool,
    ) -> ProjectReconciliation:
        progress = metadata.progress or scan_project_progress(metadata.workflow_type, root, metadata.latest_task_status)
        latest_status = _latest_status(metadata, latest_task)
        warnings: List[ReconciliationWarning] = []
        percent = int(progress.get("percent") or 0)
        if latest_status in SUMMARY_TERMINAL_STATUSES and percent == 0:
            status = RECONCILIATION_ABNORMAL_COMPLETED
            warnings.append(
                ReconciliationWarning(
                    code="missing_output",
                    message="任务记录显示已完成，但当前未检测到对应输出产物。",
                )
            )
        elif latest_status in SUMMARY_TERMINAL_STATUSES:
            status = RECONCILIATION_OK
        elif percent > 0:
            status = RECONCILIATION_STATE_INCOMPLETE
            warnings.append(
                ReconciliationWarning(
                    code="state_metadata_incomplete",
                    message="检测到已有产物，但缺少可靠的完成状态记录。",
                )
            )
        else:
            status = RECONCILIATION_INCOMPLETE
        plan = self._repair_plan(metadata, root, status, warnings, []) if include_repair_plan else None
        return ProjectReconciliation(status=status, warnings=warnings, repair_plan=plan)

    def _repair_plan(
        self,
        metadata: Any,
        root: Path,
        status: str,
        warnings: List[ReconciliationWarning],
        output_checks: List[OutputCheck],
    ) -> RepairPlan | None:
        if status == RECONCILIATION_OK or status == RECONCILIATION_INCOMPLETE:
            return None
        if status == RECONCILIATION_STATE_INCOMPLETE:
            return RepairPlan(
                project_slug=metadata.project_slug,
                status=status,
                actions=[
                    RepairAction(
                        action_id="metadata_reconcile",
                        label="校正项目状态",
                        description="重新扫描当前输出目录，并校正项目进度、历史状态和输出路径绑定；不会生成或改写总结正文。",
                        repair_kind=REPAIR_KIND_METADATA,
                        required_inputs=["project_metadata", "output_directory"],
                        estimated_scope="metadata_only",
                    )
                ],
            )
        if metadata.workflow_type != "novel_summary":
            return RepairPlan(
                project_slug=metadata.project_slug,
                status=status,
                actions=[
                    RepairAction(
                        action_id="unsupported_workflow",
                        label="暂不支持自动修复",
                        description="当前流程暂不支持自动修复，请手动检查输出目录或重新运行任务。",
                        status=REPAIR_ACTION_BLOCKED,
                        blocked_reason="该工作流暂未实现项目输出修复。",
                        repair_kind=REPAIR_KIND_UNSUPPORTED,
                    )
                ],
            )

        affected = [check.expected or check.label for check in output_checks if check.status != "present"]
        if count_text_files(root) <= 0:
            action = RepairAction(
                action_id="rerun_missing_summary_stages",
                label="补跑缺失总结阶段",
                description="缺少可用于补跑的章节文件，无法安全重建总结正文。",
                status=REPAIR_ACTION_BLOCKED,
                blocked_reason="输出目录中没有可用章节 TXT 文件。",
                required_inputs=["chapter_files", "api_config"],
                affected_outputs=affected,
                repair_kind=REPAIR_KIND_SUMMARY_CONTENT,
                requires_llm=True,
                may_change_content=True,
                estimated_scope="missing_intermediates",
            )
        else:
            action = RepairAction(
                action_id="rerun_missing_summary_stages",
                label="补跑缺失总结阶段",
                description="从现有章节和中间产物继续运行小说总结流程，补齐缺失总结正文。该操作可能调用 LLM，结果可能与原始运行不同。",
                required_inputs=["chapter_files", "api_config", "summary_settings"],
                affected_outputs=affected,
                repair_kind=REPAIR_KIND_SUMMARY_CONTENT,
                requires_llm=True,
                may_change_content=True,
                estimated_scope="missing_intermediates",
            )
        return RepairPlan(project_slug=metadata.project_slug, status=status, actions=[action])


def _latest_status(metadata: Any, latest_task: Mapping[str, Any] | None) -> str:
    if latest_task:
        return str(latest_task.get("status") or "").strip()
    return str(getattr(metadata, "latest_task_status", "") or "").strip()


def _latest_task_type(latest_task: Mapping[str, Any] | None) -> str:
    return str((latest_task or {}).get("task_type") or "").strip()


def _latest_params(latest_task: Mapping[str, Any] | None) -> Dict[str, Any]:
    params = (latest_task or {}).get("params_summary") or {}
    return dict(params) if isinstance(params, Mapping) else {}


def _load_state_files(cache_dir: Path, warnings: List[ReconciliationWarning]) -> List[Dict[str, Any]]:
    states: List[Dict[str, Any]] = []
    if not cache_dir.exists():
        return states
    for path in sorted(cache_dir.glob("state_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            warnings.append(
                ReconciliationWarning(
                    code="state_file_unreadable",
                    message=f"状态文件不可读：{path.name}",
                    paths=[str(path)],
                )
            )
            continue
        if isinstance(data, dict):
            states.append(data)
    return states


def _state_claims(states: Iterable[Mapping[str, Any]]) -> Dict[str, set[str]]:
    claims: Dict[str, set[str]] = {}
    for state in states:
        for stage in ["small_summary", "big_summary", "super_summary", "ultimate_summary"]:
            entries = state.get(stage) or {}
            if not isinstance(entries, Mapping):
                continue
            for task_name, complete in entries.items():
                if complete:
                    claims.setdefault(stage, set()).add(str(task_name))
    return claims


def _has_summary_outputs(root: Path) -> bool:
    cache_dir = root / ".summarizer_cache"
    return any(summary_file_paths(cache_dir / subdir) for subdir in SUMMARY_OUTPUT_SUBDIRS)


def _checks_for_state_claims(root: Path, claims: Mapping[str, set[str]], output_format: str) -> List[OutputCheck]:
    checks: List[OutputCheck] = []
    for task_name in sorted(claims.get("small_summary", set())):
        checks.append(_check_prefixed_output(root, USER_FACING_SMALL_PLOT_SUBDIR, task_name, f"小剧情总结 {task_name}", output_format))
        checks.append(_check_prefixed_output(root, USER_FACING_SMALL_CHAR_SUBDIR, task_name, f"小角色总结 {task_name}", output_format))
    for task_key in sorted(claims.get("big_summary", set())):
        if task_key.endswith("_plot"):
            task_name = task_key.removesuffix("_plot")
            checks.append(_check_prefixed_output(root, USER_FACING_BIG_PLOT_SUBDIR, f"{task_name}_", f"剧情大总结 {task_name}", output_format))
        elif task_key.endswith("_char"):
            task_name = task_key.removesuffix("_char")
            checks.append(_check_prefixed_output(root, USER_FACING_BIG_CHAR_SUBDIR, f"{task_name}_", f"角色大总结 {task_name}", output_format))
    for task_key in sorted(claims.get("super_summary", set())):
        if task_key.endswith("_plot"):
            task_name = task_key.removesuffix("_plot")
            checks.append(_check_prefixed_output(root, USER_FACING_SUPER_PLOT_P1_SUBDIR, f"super_summary_{task_name}_plot_p1", f"超级剧情总结 P1 {task_name}", output_format))
            checks.append(_check_prefixed_output(root, USER_FACING_SUPER_PLOT_P2_SUBDIR, f"super_summary_{task_name}_plot_p2", f"超级剧情总结 P2 {task_name}", output_format))
        elif task_key.endswith("_char"):
            task_name = task_key.removesuffix("_char")
            checks.append(_check_prefixed_output(root, USER_FACING_SUPER_CHAR_P1_SUBDIR, f"super_summary_{task_name}_char_p1", f"超级角色总结 P1 {task_name}", output_format))
            checks.append(_check_prefixed_output(root, USER_FACING_SUPER_CHAR_P2_SUBDIR, f"super_summary_{task_name}_char_p2", f"超级角色总结 P2 {task_name}", output_format))
    for task_name, subdir, label in ULTIMATE_CHECKS:
        if task_name in claims.get("ultimate_summary", set()):
            checks.append(_check_prefixed_output(root, subdir, f"{task_name}_", label, output_format))
    return checks


def _checks_for_ultimate_outputs(root: Path, output_format: str) -> List[OutputCheck]:
    return [
        _check_prefixed_output(root, subdir, f"{task_name}_", label, output_format)
        for task_name, subdir, label in ULTIMATE_CHECKS
    ]


def _check_small_summary_coverage(root: Path, chapter_count: int) -> OutputCheck:
    completed = count_small_summary_covered_chapters(root / ".summarizer_cache")
    if chapter_count > 0 and completed >= chapter_count:
        return OutputCheck(
            id="small_summary_coverage",
            label="小总结覆盖",
            status="present",
            expected=f"{chapter_count} 个章节",
            actual=f"{completed} 个章节",
        )
    return OutputCheck(
        id="small_summary_coverage",
        label="小总结覆盖",
        status="missing",
        expected=f"{chapter_count} 个章节",
        actual=f"{completed} 个章节",
        message="小总结覆盖不完整",
    )


def _check_prefixed_output(root: Path, subdir: str, prefix: str, label: str, output_format: str) -> OutputCheck:
    directory = root / ".summarizer_cache" / subdir
    expected_suffix = f".{output_format}"
    files = [
        item
        for item in summary_file_paths(directory)
        if item.name.startswith(prefix)
    ]
    expected = str(directory / f"{prefix}*{expected_suffix}")
    if not files:
        return OutputCheck(
            id=_check_id(label),
            label=label,
            status="missing",
            expected=expected,
            message="未找到对应输出文件",
        )
    if not any(item.suffix.lower() == expected_suffix for item in files):
        return OutputCheck(
            id=_check_id(label),
            label=label,
            status="format_mismatch",
            expected=expected,
            actual=", ".join(str(item) for item in files),
            message=f"存在输出文件，但不是当前保存的 {output_format} 格式",
        )
    return OutputCheck(
        id=_check_id(label),
        label=label,
        status="present",
        expected=expected,
        actual=", ".join(str(item) for item in files if item.suffix.lower() == expected_suffix),
    )


def _check_id(label: str) -> str:
    return "_".join(part for part in label.lower().replace("-", "_").split() if part)
