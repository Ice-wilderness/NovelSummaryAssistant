## Why

稳定性审计文档中的后续状态已经落后于当前归档变更：`project_workspace.py` 拆分已完成并归档，但总览和 backlog 仍把它列为未实现事项。现在先校准文档，可以避免后续 OpenSpec 规划继续依据过期风险排序。

## What Changes

- 更新 `docs/stability_audit/00-overview.md` 和 `docs/stability_audit/follow-up-backlog.md`，把项目工作区服务拆分从未实现项移到已实现项，并调整后续优先级。
- 更新 README 中与后端入口和项目工作区模块职责相关的项目结构描述，使其反映当前 `routes/` 与 `workspace_services/` 拆分后的布局。
- 保留原始模块审计报告中的历史发现语境，但在总览/backlog 中明确当前判断以最新归档 change 和代码布局为准。
- 不修改运行时行为、API 契约、持久化格式、依赖或测试策略。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `module-stability-audit-reports`: 要求稳定性审计的跟进状态文档能够反映已归档变更和当前模块布局，避免已完成事项继续出现在未实现优先级中。

## Impact

- 影响文档：`docs/stability_audit/00-overview.md`、`docs/stability_audit/follow-up-backlog.md`、`README.md`。
- 影响 OpenSpec：为 `module-stability-audit-reports` 增加文档状态同步要求。
- 不影响后端/前端运行时代码，不新增依赖。
