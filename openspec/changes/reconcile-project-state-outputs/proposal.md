## Why

稳定性审计发现，项目完成状态同时依赖 JSON 状态、任务摘要、中间产物和最终输出文件；当用户手工删除输出、导入旧项目、切换输出格式或迁移目录后，历史项目可能被误判为正常完成或普通未完成。现在需要把“曾经完成但当前产物异常”和“从未完成”区分开，并为可安全补齐的缺失产物提供用户显式触发的修复/续跑路径。

## What Changes

- 在项目进入、历史项目加载和导入项目时执行状态/输出 reconcile，统一判断任务摘要、项目进度文件、中间产物和最终输出文件的一致性。
- 引入“异常完成”状态：当状态记录显示已完成或部分完成，但关键输出文件缺失、格式不匹配或产物不可读时，项目历史和详情应保留完成事实并显示可操作 warning。
- 为异常项目生成 repair plan，区分可从现有中间产物补齐、需要重新调用 LLM、缺少源文件/配置无法修复、存在覆盖风险等情况。
- 提供用户显式触发的修复/续跑任务：只在用户确认后补齐缺失输出或重新生成缺失阶段；涉及 LLM 调用、覆盖已有文件或结果可能变化时必须提前披露。
- 保持保守兼容：旧项目、旧任务摘要和缺少新 reconcile 字段的记录仍可加载；无法确认的项目不得静默标为成功，也不得静默调用 LLM。
- 补充后端和前端 focused tests，覆盖异常完成识别、repair plan 生成、用户确认后的修复任务、不可修复提示和历史项目展示。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `managed-project-outputs`: 扩展项目状态识别契约，要求对状态文件、任务摘要、中间产物和输出文件执行 reconcile，并返回异常完成、warning 与 repair plan。
- `task-runtime-api`: 扩展任务 API 契约，支持用户显式触发的项目输出修复/续跑任务，并定义其任务状态、费用/覆盖披露和失败语义。
- `webui-workbench`: 扩展前端工作台契约，要求历史项目、项目详情和总结页面展示异常完成状态、修复建议和用户确认后的修复入口。

## Impact

- 后端：`webui_backend/project_workspace.py` 及其拆分服务、项目状态识别 helper、任务启动/恢复路由、`webui_backend/task_runtime.py`、总结工作流 runner 和输出文件解析/写入 helper。
- 前端：项目历史控件、小说总结页面、共享任务状态展示、API client 类型、修复确认对话框或操作区，以及异常完成 warning 展示。
- 数据兼容：新增 reconcile/repair 字段必须兼容旧 metadata、旧任务摘要和已导入目录；读取失败时返回 warning 而不是阻塞整个项目列表。
- 成本与覆盖：任何会重新调用 LLM 或覆盖/重写输出文件的修复动作都必须由用户确认，并在任务开始前说明可能产生费用和结果差异。
- 测试：新增或扩展 `tests/test_project_workspace.py`、`tests/test_api_app.py`、`tests/test_workflow_services.py`，以及对应前端 Vitest focused tests。
