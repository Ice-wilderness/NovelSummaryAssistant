## Why

稳定性审计发现，`TaskRuntime` 的任务记录和事件历史主要保存在进程内，后端重启后前端无法查询旧任务终态，运行中的任务也可能只留下项目 metadata 的模糊状态。下一步应先让终态任务摘要可持久化、可查询、可展示，并明确重启期间运行中的任务不会自动恢复执行。

## What Changes

- 为已进入 `completed`、`failed`、`cancelled` 或 `partial_failed` 的任务写入 terminal task summary，后端重启后仍可通过任务状态查询和项目历史恢复关键状态。
- 对后端重启时仍处于 `running`、`paused` 或其他非终态的任务，标记为中断/未知恢复状态，并向前端提供可显示的提示，要求用户重新启动或从项目进度继续。
- 保留现有实时 SSE 行为和终态事件结束行为；本 change 不实现完整事件日志落盘、`Last-Event-ID` 回放、SSE heartbeat 或自动恢复正在执行的后台任务。
- 项目历史和共享任务状态展示需要区分“已持久化终态”和“服务重启导致运行中任务中断”，避免把中断误显示为普通失败、完成或取消。
- 补充后端和前端 focused tests，覆盖终态摘要落盘、重启后查询、非终态中断提示、项目历史展示和旧数据兼容。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `task-runtime-api`: 扩展任务状态查询和项目历史契约，要求终态任务摘要持久化，并定义后端重启后非终态任务的中断状态表达。
- `webui-workbench`: 要求前端展示持久化终态任务和重启中断提示，不把中断状态重映射为普通失败或成功。

## Impact

- 后端：`webui_backend/task_runtime.py`、任务响应模型、项目 metadata/历史更新路径、相关 API 路由或 workspace service helper。
- 前端：`frontend/src/hooks/useTaskActions.ts`、共享任务状态展示、项目历史状态标签，以及小说/文章/自定义/分割/雷点扫描页面的任务恢复提示。
- 数据兼容：旧项目或旧任务可能没有 terminal summary；读取时应兼容缺失，并继续依赖现有项目进度识别。
- 测试：新增或扩展 `tests/test_task_runtime.py`、`tests/test_api_app.py`、项目历史相关测试，以及对应 Vitest focused tests。
