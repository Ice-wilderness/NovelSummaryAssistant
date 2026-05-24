# 雷点扫描工作流审计

## 模块职责

雷点扫描覆盖前端扫描配置和结果复核、后端任务启动、章节段落索引、LLM 精确扫描、可选验证、finding 过滤、事件聚合、报告持久化和导出。

## 关键入口

- `frontend/src/views/TriggerScanPage.tsx`
- `webui_backend/api_app.py`
- `webui_backend/workflow_services.py`
- `webui_backend/trigger_models.py`
- `webui_backend/trigger_profile_service.py`
- `logic/trigger_scan/pipeline.py`
- `logic/trigger_scan/scan_state.py`
- `logic/trigger_scan/reporting.py`
- `logic/paragraph_index.py`

## 发现

### 高风险：暂停在雷点扫描核心路径中基本不阻塞

- 现象：精确扫描和验证阶段调用 `await asyncio.to_thread(pause_signal.wait, 0)`。
- 证据：`PauseSignal.wait(0)` 使用 0 秒 timeout，会立即返回，不会等待用户恢复。
- 影响：用户点击暂停后，雷点扫描 worker 仍可能继续执行 API 调用和写报告。
- 风险级别：高。
- 建议：改为复用 `logic.utils.check_pause_async` 或调用无 timeout 的 wait；补充暂停/恢复测试。

### 高风险：续扫进度统计口径错误

- 现象：续扫时 `completed_from_resume` 被放入 stage completed，但 total 使用 pending 章节数；后续 worker 又用本次 `processed_chapters` 覆盖 completed。
- 证据：`workflow_services.py` 初始化精确扫描阶段时 `completed=completed_from_resume, total=len(precise_chapters)`，worker 更新时 `completed=processed_chapters`。
- 影响：续扫 UI 可能显示完成数大于总数，或从已完成数回退到 1/剩余数。
- 风险级别：高。
- 建议：同时保留 selected total、resume completed、current processed，统一展示 `completed_from_resume + processed_chapters` / `selected_total`。

### 高风险：续扫后的验证上下文可能缺失

- 现象：`all_findings` 在续扫时包含旧报告 findings，但 `indexes_by_name` 只在当前 pending 章节处理时填充。
- 证据：验证阶段对 `all_findings` 构建 verification batches，再通过 `_context_for_findings(batch, indexes_by_name)` 提取段落上下文。
- 影响：旧 finding 在续扫验证时可能没有段落上下文，造成误删、误判或提示词质量下降。
- 风险级别：高。
- 建议：续扫验证前为所有待验证 finding 的章节重建 paragraph index，或只验证本轮新增 findings。

### 中风险：聚合提示词契约漂移

- 现象：后端加载并渲染 aggregation prompt，但实际聚合使用 `merge_adjacent_findings` 和 `aggregate_findings_into_events` 的确定性逻辑，没有调用 LLM。
- 证据：`workflow_services.py` 渲染 `TRIGGER_AGGREGATION_PROMPT_KEY` 后直接调用本地聚合函数。
- 影响：OpenSpec 和提示词编辑器会让维护者以为聚合提示词会影响结果，但实际无效。
- 风险级别：中。
- 建议：要么删除/隐藏 aggregation prompt 并更新 spec，要么真正调用 LLM 聚合并解析 ScanEvent。

### 中风险：部分失败会被写成 completed

- 现象：雷点扫描异常时如果已有 findings，报告状态被设置为 completed。
- 证据：`workflow_services.py` 的异常处理分支：有 findings 时 `report.status = "completed"`，否则 failed。
- 影响：部分扫描失败可能被用户误认为完整成功，尤其是在后续验证或报告阶段失败时。
- 风险级别：中。
- 建议：引入 `partial_failed` 或 `completed_with_errors` 状态，并在报告和 UI 中区分。

## 优化空间

- 明确雷点扫描状态机：running、paused、cancelled、failed、partial、completed。
- 将 runner 内部嵌套函数拆成可测试的服务函数。
- 为续扫、暂停、部分失败和聚合契约补充定向测试。

## 验证

- `python -m pytest` 通过，包含 pipeline、prompts、reporting、trigger models 和 profile service 测试。
- 当前测试没有覆盖“真实暂停阻塞”和“续扫进度口径”这两个高风险点。
