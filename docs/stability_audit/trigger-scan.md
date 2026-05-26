# 雷点扫描工作流审计

## 模块职责

雷点扫描覆盖前端扫描配置和结果复核、后端任务启动、章节段落索引、LLM 精确扫描、可选验证、finding 过滤、事件聚合、报告持久化和导出。

## 关键入口

- `frontend/src/views/TriggerScanPage.tsx`
- `frontend/src/views/trigger-scan/`
- `webui_backend/api_app.py`
- `webui_backend/workflow_services.py`
- `webui_backend/trigger_models.py`
- `webui_backend/trigger_profile_service.py`
- `logic/trigger_scan/pipeline.py`
- `logic/trigger_scan/scan_state.py`
- `logic/trigger_scan/reporting.py`
- `logic/paragraph_index.py`

## 发现

### 已治理：暂停在雷点扫描核心路径中基本不阻塞

- 现象：精确扫描和验证阶段调用 `await asyncio.to_thread(pause_signal.wait, 0)`。
- 证据：`PauseSignal.wait(0)` 使用 0 秒 timeout，会立即返回，不会等待用户恢复。
- 影响：用户点击暂停后，雷点扫描 worker 仍可能继续执行 API 调用和写报告。
- 原始风险级别：高。
- 当前状态：已改为真正阻塞的异步暂停门，并补充暂停阻塞验证；后续维护扫描 worker 时仍应复用同一暂停检查路径。

### 已治理：续扫进度统计口径错误

- 现象：续扫时 `completed_from_resume` 被放入 stage completed，但 total 使用 pending 章节数；后续 worker 又用本次 `processed_chapters` 覆盖 completed。
- 证据：`workflow_services.py` 初始化精确扫描阶段时 `completed=completed_from_resume, total=len(precise_chapters)`，worker 更新时 `completed=processed_chapters`。
- 影响：续扫 UI 可能显示完成数大于总数，或从已完成数回退到 1/剩余数。
- 原始风险级别：高。
- 当前状态：续扫进度已统一使用 `selected_total`、`completed_from_resume`、`pending_total` 和 `processed_current_run`；前端配置页继续展示已完成/待扫描口径。

### 已治理：续扫后的验证上下文可能缺失

- 现象：`all_findings` 在续扫时包含旧报告 findings，但 `indexes_by_name` 只在当前 pending 章节处理时填充。
- 证据：验证阶段对 `all_findings` 构建 verification batches，再通过 `_context_for_findings(batch, indexes_by_name)` 提取段落上下文。
- 影响：旧 finding 在续扫验证时可能没有段落上下文，造成误删、误判或提示词质量下降。
- 原始风险级别：高。
- 当前状态：历史 finding 验证会区分新增和历史来源，缺失上下文时保留 finding 并标记 `unverified` warning，不再静默误判。

### 已澄清：聚合提示词契约漂移

- 现象：后端加载并渲染 aggregation prompt，但实际聚合使用 `merge_adjacent_findings` 和 `aggregate_findings_into_events` 的确定性逻辑，没有调用 LLM。
- 证据：`workflow_services.py` 渲染 `TRIGGER_AGGREGATION_PROMPT_KEY` 后直接调用本地聚合函数。
- 影响：OpenSpec 和提示词编辑器会让维护者以为聚合提示词会影响结果，但实际无效。
- 原始风险级别：中。
- 当前状态：当前实现明确为 deterministic aggregation；提示词契约和前端文案已调整，后续 LLM 聚合需另立 change 设计成本、fallback、JSON 解析和 UI 披露。

### 已治理：部分失败会被写成 completed

- 现象：雷点扫描异常时如果已有 findings，报告状态被设置为 completed。
- 证据：`workflow_services.py` 的异常处理分支：有 findings 时 `report.status = "completed"`，否则 failed。
- 影响：部分扫描失败可能被用户误认为完整成功，尤其是在后续验证或报告阶段失败时。
- 原始风险级别：中。
- 当前状态：非取消的部分结果使用 `partial_failed` 并展示 warning；用户取消使用 `cancelled`，不会写成普通完成。

### 已治理：雷点扫描页面职责过度集中

- 现象：雷点扫描前端页面曾集中承担档案、扫描配置、任务控制、报告历史、finding 复核和上下文弹窗。
- 当前状态：`TriggerScanPage.tsx` 已拆出 `frontend/src/views/trigger-scan/` 领域模块；维护 profile、scan config、results、context modal 和 display/filter helper 时应优先进入对应模块。
- 验证：新增 Vitest + Testing Library 测试覆盖 display、result filters、profile draft、ProfileTab、ScanConfigTab、ResultsTab 和 ContextModal。

## 优化空间

- 明确雷点扫描状态机：running、paused、cancelled、failed、partial、completed。
- 将 runner 内部嵌套函数拆成可测试的服务函数。
- 继续补充更接近端到端的 WebUI 交互测试，尤其是真实浏览器里的任务事件、报告切换和上下文查看。

## 验证

- `python -m pytest` 通过，包含 pipeline、prompts、reporting、trigger models 和 profile service 测试。
- `npm run test` 通过，包含雷点扫描前端拆分边界测试。
- `npm run build` 通过。
