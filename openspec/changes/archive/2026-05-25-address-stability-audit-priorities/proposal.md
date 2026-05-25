## Why

稳定性审计显示，当前主路径测试和前端构建可通过，但长任务控制、雷点扫描续扫/报告状态、提示词契约和输出目录删除边界存在会影响用户判断和数据安全的高优先级风险。现在需要把这些审计结论收敛为一组可验证的修复任务，先统一运行时语义，再处理后续可维护性拆分。

## What Changes

- 统一长任务取消语义：小说总结、文章总结、自定义总结、章节分割和雷点扫描的用户取消都应传播到任务运行时，并以 `cancelled` 作为终态。
- 修复雷点扫描暂停、续扫进度和验证边界：暂停必须真正阻塞后续 API 调用；续扫进度使用选中章节总量作为总口径；续扫时只复验未验证或验证状态不明的历史 finding，新 finding 正常验证，无法验证的结果需要明确 warning。
- 明确雷点扫描报告状态：只有选中章节全部完成扫描且后续阶段成功时才标记 `completed`；非取消异常导致部分章节未扫描完时标记 `partial_failed` 并保留可用结果。
- 修正聚合提示词契约：本次保持本地 deterministic 聚合，不引入额外 LLM 聚合调用；提示词编辑器和 OpenSpec 必须明确 aggregation prompt 当前不参与运行时 LLM 调用。
- 保留完整 API 失败诊断输入输出以支持排查，同时维持密钥脱敏，并补充日志保留/清理策略，不默认截断用户内容。
- 加强项目输出目录删除保护：只删除系统管理且可证明 ownership 的导出目录；自定义或无法证明归属的目录必须保留。
- 补充针对取消、暂停、续扫、部分失败、输出目录 ownership 和提示词契约的定向测试。
- 记录后续计划：将“使用 LLM aggregation prompt 生成 ScanEvent”的 B 方案保留为后续独立 change，避免本次稳定性修复引入新的模型调用风险。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `task-runtime-api`: 统一取消终态、任务事件结束行为和 API 失败诊断保留策略。
- `trigger-scan-workflow`: 修复暂停等待、续扫进度、历史 finding 验证策略和 deterministic 聚合契约。
- `trigger-scan-results`: 增加 `partial_failed`/未验证 warning 的报告语义，并要求 `completed` 只用于完整扫描成功。
- `workflow-prompt-composition`: 明确 trigger scan aggregation prompt 当前不参与 LLM 调用，并记录 LLM 聚合作为后续计划。
- `managed-project-outputs`: 为托管导出目录增加 ownership 边界，避免删除自定义或归属不明的用户目录。
- `webui-workbench`: 显示 cancelled、partial_failed、unverified warning 和聚合提示词状态，并在任务事件断开后刷新任务状态。

## Impact

- 后端：`webui_backend/task_runtime.py`、`webui_backend/workflow_services.py`、`webui_backend/api_app.py`、`webui_backend/project_workspace.py`、`logic/orchestrator.py`、`logic/article_summary_logic.py`、`logic/custom_summary_logic.py`、`logic/trigger_scan/*`、`logic/llm_api.py`、`logic/utils.py`。
- 前端：`frontend/src/hooks/useTaskActions.ts`、`frontend/src/views/TriggerScanPage.tsx`、`frontend/src/views/PromptEditorPage.tsx`、`frontend/src/api/client.ts` 以及相关状态展示组件。
- 数据与兼容性：新增或扩展任务/报告状态字段、trigger scan report warnings、输出目录 ownership metadata；旧报告和旧项目需要兼容读取。
- 测试：新增 Python runner 级测试和 trigger scan 状态测试；前端至少补充关键 hook/API client 行为测试或等价验证。
