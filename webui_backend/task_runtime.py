from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELING = "canceling"
    CANCELLED = "cancelled"
    PARTIAL_FAILED = "partial_failed"
    SUCCESS = "success"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class TaskType(str, Enum):
    NOVEL_SUMMARY = "novel_summary"
    SMALL_SUMMARY_PREPARATION = "small_summary_preparation"
    TRIGGER_SCAN = "trigger_scan"
    ARTICLE_SUMMARY = "article_summary"
    CUSTOM_SUMMARY = "custom_summary"
    CHAPTER_SPLIT = "chapter_split"
    MODEL_FETCH = "model_fetch"


TERMINAL_TASK_STATUSES = frozenset(
    {
        TaskStatus.SUCCESS,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.PARTIAL_FAILED,
    }
)
ACTIVE_TASK_STATUSES = frozenset(
    {
        TaskStatus.PENDING,
        TaskStatus.RUNNING,
        TaskStatus.PAUSED,
        TaskStatus.CANCELING,
    }
)
INACTIVE_TASK_STATUSES = TERMINAL_TASK_STATUSES | frozenset({TaskStatus.INTERRUPTED})
INTERRUPTED_TASK_MESSAGE = (
    "后端重启时任务仍未结束，无法自动恢复，请重新启动任务或从项目进度继续。"
)


def _status_value(status: TaskStatus | str | None) -> str:
    return str(getattr(status, "value", status) or "").strip().lower()


def is_terminal_task_status(status: TaskStatus | str | None) -> bool:
    return _status_value(status) in {item.value for item in TERMINAL_TASK_STATUSES}


def is_active_task_status(status: TaskStatus | str | None) -> bool:
    return _status_value(status) in {item.value for item in ACTIVE_TASK_STATUSES}


def is_inactive_task_status(status: TaskStatus | str | None) -> bool:
    return _status_value(status) in {item.value for item in INACTIVE_TASK_STATUSES}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


@dataclass
class TaskEvent:
    task_id: str
    event_type: str
    message: str = ""
    source_id: str = "global"
    status: Optional[str] = None
    progress_text: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskEvent":
        return cls(
            task_id=str(data.get("task_id", "")),
            event_type=str(data.get("event_type", "")),
            message=str(data.get("message", "")),
            source_id=str(data.get("source_id", "global")),
            status=(
                None
                if data.get("status") is None
                else str(data.get("status"))
            ),
            progress_text=(
                None
                if data.get("progress_text") is None
                else str(data.get("progress_text"))
            ),
            data=dict(data.get("data") or {}),
            timestamp=float(data.get("timestamp", time.time()) or time.time()),
        )


@dataclass
class TaskRecord:
    task_id: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    progress_text: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    result_summary: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    result_data: Dict[str, Any] = field(default_factory=dict)
    params_summary: Dict[str, Any] = field(default_factory=dict)
    events: List[TaskEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["events"] = [event.to_dict() for event in self.events]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskRecord":
        status = TaskStatus(str(data.get("status") or TaskStatus.PENDING.value))
        events = [
            TaskEvent.from_dict(item)
            for item in data.get("events", [])
            if isinstance(item, dict)
        ]
        warnings = data.get("warnings") or []
        if not isinstance(warnings, list):
            warnings = []
        result_data = data.get("result_data") or {}
        if not isinstance(result_data, dict):
            result_data = {}
        params_summary = data.get("params_summary") or {}
        if not isinstance(params_summary, dict):
            params_summary = {}
        return cls(
            task_id=str(data.get("task_id", "")),
            task_type=str(data.get("task_type", "")),
            status=status,
            progress_text=str(data.get("progress_text", "")),
            created_at=float(data.get("created_at", time.time()) or time.time()),
            updated_at=float(data.get("updated_at", time.time()) or time.time()),
            finished_at=(
                None
                if data.get("finished_at") is None
                else float(data.get("finished_at"))
            ),
            result_summary=(
                None
                if data.get("result_summary") is None
                else str(data.get("result_summary"))
            ),
            error=None if data.get("error") is None else str(data.get("error")),
            warnings=[str(item) for item in warnings],
            result_data=result_data,
            params_summary=params_summary,
            events=events,
        )


@dataclass
class TaskRunOutcome:
    status: TaskStatus | str = TaskStatus.SUCCESS
    result_summary: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)


class PauseSignal:
    """Compatibility pause signal for existing logic.check_pause_async."""

    def __init__(self) -> None:
        self._paused = False
        self._resume_event = threading.Event()
        self._resume_event.set()

    def set(self) -> None:
        self._paused = True
        self._resume_event.clear()

    def clear(self) -> None:
        self._paused = False
        self._resume_event.set()

    def is_set(self) -> bool:
        return self._paused

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._resume_event.wait(timeout)


RunnerResult = Union[Optional[str], TaskRunOutcome]
Runner = Callable[[TaskRecord, PauseSignal, Callable[..., None]], Awaitable[RunnerResult]]


def _runner_result_is_failure(result_summary: Optional[str]) -> bool:
    if result_summary is None:
        return False
    normalized = str(result_summary).strip().lower()
    return normalized == "failed" or normalized.startswith("error:")


def _normalize_runner_outcome(result: RunnerResult) -> TaskRunOutcome:
    if isinstance(result, TaskRunOutcome):
        status = result.status if isinstance(result.status, TaskStatus) else TaskStatus(str(result.status))
        return TaskRunOutcome(
            status=status,
            result_summary=result.result_summary,
            error=result.error,
            warnings=list(result.warnings),
            data=dict(result.data),
        )
    if _runner_result_is_failure(result):
        return TaskRunOutcome(
            status=TaskStatus.FAILED,
            result_summary=result,
            error=str(result or "Task failed"),
        )
    return TaskRunOutcome(status=TaskStatus.SUCCESS, result_summary=result)


@dataclass
class _TaskHandle:
    record: TaskRecord
    pause_signal: PauseSignal
    event_queue: asyncio.Queue
    asyncio_task: Optional[asyncio.Task] = None


class TaskRuntime:
    def __init__(self, task_summary_dir: str | Path | None = None) -> None:
        self._handles: Dict[str, _TaskHandle] = {}
        self._task_summary_dir = Path(task_summary_dir) if task_summary_dir else None
        self._load_persisted_summaries()

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        handle = self._handles.get(task_id)
        return handle.record if handle else None

    def list_tasks(self) -> List[TaskRecord]:
        return [handle.record for handle in self._handles.values()]

    async def start_task(
        self,
        task_type: TaskType | str,
        runner: Runner,
        params_summary: Optional[Dict[str, Any]] = None,
    ) -> TaskRecord:
        task_id = uuid.uuid4().hex
        record = TaskRecord(
            task_id=task_id,
            task_type=task_type.value if isinstance(task_type, TaskType) else str(task_type),
            params_summary=params_summary or {},
        )
        handle = _TaskHandle(
            record=record,
            pause_signal=PauseSignal(),
            event_queue=asyncio.Queue(),
        )
        self._handles[task_id] = handle
        self._persist_record(record)
        handle.asyncio_task = asyncio.create_task(self._run(handle, runner))
        return record

    def emit_event(
        self,
        task_id: str,
        event_type: str,
        message: str = "",
        source_id: str = "global",
        status: Optional[str] = None,
        progress_text: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> TaskEvent:
        handle = self._require_handle(task_id)
        event = TaskEvent(
            task_id=task_id,
            event_type=event_type,
            message=message,
            source_id=source_id,
            status=status,
            progress_text=progress_text,
            data=data or {},
        )
        handle.record.events.append(event)
        if progress_text:
            handle.record.progress_text = progress_text
        handle.record.updated_at = event.timestamp
        handle.event_queue.put_nowait(event)
        self._persist_record(handle.record)
        return event

    def has_active_task(self, task_types: Optional[set[str]] = None) -> bool:
        for handle in self._handles.values():
            if not is_active_task_status(handle.record.status):
                continue
            if task_types is None or handle.record.task_type in task_types:
                return True
        return False

    async def next_event(self, task_id: str) -> TaskEvent:
        handle = self._require_handle(task_id)
        return await handle.event_queue.get()

    def pause_task(self, task_id: str) -> TaskRecord:
        handle = self._require_handle(task_id)
        if handle.record.status == TaskStatus.RUNNING:
            handle.pause_signal.set()
            self._set_status(handle, TaskStatus.PAUSED)
            self.emit_event(task_id, "state", "Task paused", status=TaskStatus.PAUSED.value)
        return handle.record

    def resume_task(self, task_id: str) -> TaskRecord:
        handle = self._require_handle(task_id)
        if handle.record.status == TaskStatus.PAUSED:
            handle.pause_signal.clear()
            self._set_status(handle, TaskStatus.RUNNING)
            self.emit_event(task_id, "state", "Task resumed", status=TaskStatus.RUNNING.value)
        return handle.record

    def cancel_task(self, task_id: str) -> TaskRecord:
        handle = self._require_handle(task_id)
        if handle.asyncio_task and not handle.asyncio_task.done():
            self._set_status(handle, TaskStatus.CANCELING)
            self.emit_event(task_id, "state", "Task cancellation requested", status=TaskStatus.CANCELING.value)
            handle.asyncio_task.cancel()
        return handle.record

    async def wait_for_terminal(self, task_id: str) -> TaskRecord:
        handle = self._require_handle(task_id)
        if handle.asyncio_task:
            try:
                await handle.asyncio_task
            except asyncio.CancelledError:
                pass
        return handle.record

    async def _run(self, handle: _TaskHandle, runner: Runner) -> None:
        record = handle.record
        self._set_status(handle, TaskStatus.RUNNING)
        self.emit_event(record.task_id, "state", "Task started", status=TaskStatus.RUNNING.value)

        def emit(**kwargs):
            self.emit_event(record.task_id, **kwargs)

        try:
            outcome = _normalize_runner_outcome(await runner(record, handle.pause_signal, emit))
            record.result_summary = outcome.result_summary
            record.error = outcome.error
            record.warnings = outcome.warnings
            record.result_data = outcome.data
            if outcome.status == TaskStatus.FAILED:
                record.error = record.error or str(outcome.result_summary or "Task failed")
                self._set_status(handle, TaskStatus.FAILED, finished=True)
                self.emit_event(record.task_id, "error", record.error, status=TaskStatus.FAILED.value)
                return
            if outcome.status == TaskStatus.PARTIAL_FAILED:
                self._set_status(handle, TaskStatus.PARTIAL_FAILED, finished=True)
                self.emit_event(
                    record.task_id,
                    "state",
                    "Task partially failed",
                    status=TaskStatus.PARTIAL_FAILED.value,
                    data={"warnings": record.warnings, "result_data": record.result_data},
                )
                return
            self._set_status(handle, TaskStatus.SUCCESS, finished=True)
            self.emit_event(record.task_id, "state", "Task completed", status=TaskStatus.SUCCESS.value)
        except asyncio.CancelledError:
            self._set_status(handle, TaskStatus.CANCELLED, finished=True)
            self.emit_event(record.task_id, "state", "Task cancelled", status=TaskStatus.CANCELLED.value)
        except Exception as exc:
            record.error = f"{type(exc).__name__}: {exc}"
            self._set_status(handle, TaskStatus.FAILED, finished=True)
            self.emit_event(record.task_id, "error", record.error, status=TaskStatus.FAILED.value)

    def _set_status(self, handle: _TaskHandle, status: TaskStatus, finished: bool = False) -> None:
        now = time.time()
        handle.record.status = status
        handle.record.updated_at = now
        if finished:
            handle.record.finished_at = now
        self._persist_record(handle.record)

    def _require_handle(self, task_id: str) -> _TaskHandle:
        handle = self._handles.get(task_id)
        if not handle:
            raise KeyError(f"Unknown task_id: {task_id}")
        return handle

    def _summary_path(self, task_id: str) -> Optional[Path]:
        if not self._task_summary_dir:
            return None
        return self._task_summary_dir / f"{task_id}.json"

    def _summary_events(self, record: TaskRecord) -> List[TaskEvent]:
        for event in reversed(record.events):
            if event.status and is_inactive_task_status(event.status):
                return [event]
        for event in reversed(record.events):
            if _status_value(event.status) == record.status.value:
                return [event]
        return []

    def _summary_dict(self, record: TaskRecord) -> Dict[str, Any]:
        data = record.to_dict()
        data["events"] = [event.to_dict() for event in self._summary_events(record)]
        return _json_safe(data)

    def _persist_record(self, record: TaskRecord) -> None:
        path = self._summary_path(record.task_id)
        if not path:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = path.with_suffix(".json.tmp")
            temp_path.write_text(
                json.dumps(self._summary_dict(record), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(path)
        except (OSError, TypeError, ValueError):
            return

    def _load_persisted_summaries(self) -> None:
        if not self._task_summary_dir or not self._task_summary_dir.exists():
            return
        for path in sorted(self._task_summary_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    continue
                record = TaskRecord.from_dict(raw)
                if not record.task_id or record.task_id != path.stem:
                    continue
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue

            if is_active_task_status(record.status):
                self._mark_loaded_interrupted(record)
                self._persist_record(record)
            else:
                changed = self._ensure_summary_event(record)
                if changed:
                    self._persist_record(record)
            self._handles[record.task_id] = _TaskHandle(
                record=record,
                pause_signal=PauseSignal(),
                event_queue=asyncio.Queue(),
                asyncio_task=None,
            )

    def _mark_loaded_interrupted(self, record: TaskRecord) -> None:
        previous_status = record.status.value
        now = time.time()
        record.status = TaskStatus.INTERRUPTED
        record.updated_at = now
        record.finished_at = record.finished_at or now
        record.error = record.error or INTERRUPTED_TASK_MESSAGE
        if INTERRUPTED_TASK_MESSAGE not in record.warnings:
            record.warnings.append(INTERRUPTED_TASK_MESSAGE)
        if not record.progress_text:
            record.progress_text = "任务已中断"
        record.events = [
            TaskEvent(
                task_id=record.task_id,
                event_type="state",
                message=INTERRUPTED_TASK_MESSAGE,
                status=TaskStatus.INTERRUPTED.value,
                progress_text=record.progress_text,
                data={"previous_status": previous_status},
                timestamp=now,
            )
        ]

    def _ensure_summary_event(self, record: TaskRecord) -> bool:
        if not is_inactive_task_status(record.status):
            return False
        if any(_status_value(event.status) == record.status.value for event in record.events):
            return False
        message = record.error or record.result_summary or f"Task {record.status.value}"
        event_type = "error" if record.status == TaskStatus.FAILED else "state"
        record.events = [
            TaskEvent(
                task_id=record.task_id,
                event_type=event_type,
                message=str(message),
                status=record.status.value,
                progress_text=record.progress_text or None,
                data={
                    "warnings": record.warnings,
                    "result_data": record.result_data,
                },
                timestamp=record.updated_at,
            )
        ]
        return True
