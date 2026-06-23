import asyncio


class StageProgressTracker:
    """管理小说总结各阶段的进度状态，线程安全。"""

    def __init__(self):
        self._stages: list = []
        self._current_stage: str = ""

    def _stage_ids(self) -> set:
        return {s["id"] for s in self._stages}

    def _resolve_stage_id(self, stage_id: str, *, allow_aggregate: bool = False) -> str:
        stage_ids = self._stage_ids()
        if stage_id in stage_ids:
            return stage_id
        if allow_aggregate and stage_id in {"small_summary", "big_summary_plot", "big_summary_char"}:
            if "small_and_big_summary" in stage_ids:
                return "small_and_big_summary"
        return ""

    def init_stages(self, stages_def: list):
        """用阶段定义列表初始化，每个元素为 {"id": str, "label": str, "total": int|null}。"""
        self._stages = [
            {
                "id": s["id"],
                "label": s["label"],
                "completed": int(s.get("completed") or 0),
                "total": s.get("total"),
                "status": "pending",
            }
            for s in stages_def
        ]
        if self._stages:
            self._current_stage = self._stages[0]["id"]
            self._stages[0]["status"] = "running"

    @property
    def stages(self) -> list:
        return self._stages

    @property
    def current_stage(self) -> str:
        return self._current_stage

    def _stage_is_complete(self, stage: dict) -> bool:
        total = stage.get("total")
        if total is None:
            return True
        return stage.get("completed", 0) >= total

    def advance_stage(self, stage_id: str):
        """将指定阶段标记为 running，之前的所有阶段标记为 completed。"""
        resolved_stage_id = self._resolve_stage_id(stage_id, allow_aggregate=True)
        if not resolved_stage_id:
            return
        found = False
        for s in self._stages:
            if s["id"] == resolved_stage_id:
                s["status"] = "running"
                self._current_stage = resolved_stage_id
                found = True
            elif not found:
                s["status"] = "completed" if self._stage_is_complete(s) else "running"
            else:
                s["status"] = "pending"

    def increment(self, stage_id: str, delta: int = 1):
        """递增指定阶段的 completed 计数。"""
        resolved_stage_id = self._resolve_stage_id(stage_id, allow_aggregate=True)
        if not resolved_stage_id:
            return
        for s in self._stages:
            if s["id"] == resolved_stage_id:
                s["completed"] = min(s["completed"] + delta, s["total"] or (s["completed"] + delta))
                break

    def set_stage_completed(self, stage_id: str):
        """将指定阶段的状态设为 completed 并填满 completed 计数。"""
        resolved_stage_id = self._resolve_stage_id(stage_id)
        if not resolved_stage_id:
            return
        for s in self._stages:
            if s["id"] == resolved_stage_id:
                s["status"] = "completed"
                if s["total"]:
                    s["completed"] = s["total"]
                break

    def emit(self, emit_func):
        """通过 emit_func 发射当前进度状态。"""
        emit_stage_progress(emit_func, self._stages, self._current_stage)


def emit_stage_progress(emit_func, stages, current_stage):
    """发射结构化阶段进度事件，供前端 StageProgressBar 消费。

    - emit_func: task_runtime 的 emit(event_type, message, source_id, status, progress_text, data) 回调
    - stages: [{"id": str, "label": str, "completed": int, "total": int|null, "status": str}, ...]
    - current_stage: 当前活跃阶段的 id
    """
    if not emit_func:
        return
    progress_text = ""
    for s in stages:
        if s["id"] == current_stage:
            total_str = str(s["total"]) if s["total"] else "?"
            progress_text = f"{s['label']}: {s['completed']}/{total_str}"
            break
    emit_func(
        event_type="progress",
        message="",
        source_id="global",
        status="INFO",
        progress_text=progress_text,
        data={"stages": stages, "current_stage": current_stage},
    )


def log_message(log_callback, message, api_id=None, is_progress_log=False, progress_text=None, api_display_name=None, traceback_info=None, status=None):
    """
    一个包装器，用于将日志消息排队到GUI。
    - message: 将显示在GUI和控制台中的用户友好消息。
    - traceback_info: (可选) 仅显示在控制台中的详细回溯信息。
    - status: (可选) 日志的状态 ('START', 'SUCCESS', 'WARN', 'FAIL', 'INFO')，用于添加前缀。
    """

    status_prefixes = {
        'START': '[开始]',
        'SUCCESS': '[成功]',
        'WARN': '[警告]',
        'FAIL': '[失败]'
    }
    # 这个前缀只用于控制台日志
    prefix = status_prefixes.get(status, '')

    full_console_message = f"{prefix} {message}" if prefix else message

    # 1. 将【原始】消息和状态发送到GUI，让GUI来决定如何格式化
    if log_callback:
        log_source_id = api_display_name or api_id or "global"

        log_callback(
            source_id=log_source_id,
            message=message,
            is_progress_log=is_progress_log,
            progress_text=progress_text,
            api_id_for_log=log_source_id,  # api_id_for_log 和 source_id 在后台逻辑中是相同的
            traceback_info=traceback_info,
            status=status
        )

    # 2. 将带前缀的消息打印到控制台
    console_api_name = api_display_name or api_id or 'SYSTEM'
    print(f"[{console_api_name}] {full_console_message}")

    # 3. 如果有回溯信息，也将其打印到控制台
    if traceback_info:
        print(traceback_info)


async def check_pause_async(pause_event):
    """
    【重构】只处理暂停逻辑的异步版本。
    停止功能现在通过 asyncio.Task.cancel() 实现。
    """
    if pause_event and pause_event.is_set():
        print("任务已暂停，等待 resume...")
        # 使用 to_thread 来正确地、非阻塞地等待同步事件
        await asyncio.to_thread(pause_event.wait)
        print("任务已恢复。")
