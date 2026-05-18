from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELING = "canceling"
    CANCELLED = "cancelled"
    SUCCESS = "success"
    FAILED = "failed"


class TaskType(str, Enum):
    NOVEL_SUMMARY = "novel_summary"
    ARTICLE_SUMMARY = "article_summary"
    CUSTOM_SUMMARY = "custom_summary"
    CHAPTER_SPLIT = "chapter_split"
    MODEL_FETCH = "model_fetch"


@dataclass
class TaskEvent:
    task_id: str
    event_type: str
    message: str = ""
    source_id: str = "global"
    status: Optional[str] = None
    progress_text: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
    params_summary: Dict[str, Any] = field(default_factory=dict)
    events: List[TaskEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["events"] = [event.to_dict() for event in self.events]
        return data


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


Runner = Callable[[TaskRecord, PauseSignal, Callable[..., None]], Awaitable[Optional[str]]]


@dataclass
class _TaskHandle:
    record: TaskRecord
    pause_signal: PauseSignal
    event_queue: asyncio.Queue
    asyncio_task: Optional[asyncio.Task] = None


class TaskRuntime:
    def __init__(self) -> None:
        self._handles: Dict[str, _TaskHandle] = {}

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
    ) -> TaskEvent:
        handle = self._require_handle(task_id)
        event = TaskEvent(
            task_id=task_id,
            event_type=event_type,
            message=message,
            source_id=source_id,
            status=status,
            progress_text=progress_text,
        )
        handle.record.events.append(event)
        if progress_text:
            handle.record.progress_text = progress_text
        handle.record.updated_at = event.timestamp
        handle.event_queue.put_nowait(event)
        return event

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
            result_summary = await runner(record, handle.pause_signal, emit)
            record.result_summary = result_summary
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

    def _require_handle(self, task_id: str) -> _TaskHandle:
        handle = self._handles.get(task_id)
        if not handle:
            raise KeyError(f"Unknown task_id: {task_id}")
        return handle
