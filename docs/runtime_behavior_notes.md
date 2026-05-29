# 运行时行为维护说明

本文是维护者视角的当前运行时规则入口。它记录已经落地的行为边界，帮助后续修改任务运行时、项目工作区、配置恢复、本地路径能力和前端任务订阅时避免重新引入已治理问题。

相关审计背景见 [stability_audit/00-overview.md](stability_audit/00-overview.md) 和 [stability_audit/follow-up-backlog.md](stability_audit/follow-up-backlog.md)。

## 任务状态

任务状态由 `webui_backend/task_runtime.py` 统一管理。维护时应区分运行中状态、终态和后端重启后的非活跃状态。

| 状态 | 含义 | 维护边界 |
| --- | --- | --- |
| `pending` | 任务已创建但尚未开始执行 | 不应展示为失败或成功 |
| `running` | 任务正在执行 | 可发射进度、日志和业务事件 |
| `paused` | 任务被暂停 | 业务 runner 必须在可暂停边界真正等待恢复，不能继续发起后续 API 调用 |
| `canceling` | 用户已请求取消，取消正在传播 | runner 应保留 `asyncio.CancelledError` 传播 |
| `success` | runner 成功结束并产生可用结果 | 不代表项目当前输出一定仍完整，项目详情仍需 reconcile |
| `failed` | 任务失败且没有可用结果 | 错误应进入 task record 和事件流，便于前端展示 |
| `cancelled` | 用户取消成功 | 这是独立终态，不应包装成 `failed` |
| `partial_failed` | 有可用结果，但部分输入、阶段或扫描失败 | 必须保留 warning 和结构化失败详情，不应展示为普通成功 |
| `interrupted` | 后端重启后加载到原本非终态的持久化任务摘要 | 这是非活跃状态，不自动恢复执行；用户需要重新启动或从项目进度继续 |

雷点扫描报告有自己的报告状态集合，其中完成态使用 `completed`。不要把报告状态和通用 task status 混用。

## 任务摘要与事件流

任务运行时同时维护轻量任务摘要和可回放事件日志：

- 轻量任务摘要默认位于 `workspace/task_summaries/`，用于后端重启后查询终态任务和标记中断任务。
- 事件日志默认位于 `workspace/task_events/`，用于 SSE replay。
- 每个任务的持久化 replay 事件默认最多保留 1000 条。
- 事件日志默认清理 7 天前的文件；清理或写入失败不应阻止任务执行。

事件流规则：

- 持久化任务事件使用递增数字 `event_id`。
- SSE 帧会设置 `id: <event_id>`，前端也会读取事件 payload 中的 `event_id`。
- 客户端可通过标准 `Last-Event-ID` header 或 `last_event_id` 查询参数请求游标后的事件。
- 游标无效或早于可保留范围时，后端发送 `replay_gap` 事件，前端应立即查询任务状态兜底。
- 活跃任务空闲时发送 `heartbeat` SSE 事件。heartbeat 不写入事件日志，也不推进 replay cursor。
- 终态任务或 `interrupted` 任务的事件流应暴露最终状态并关闭。

维护 `useTaskActions`、`apiClient.subscribeTaskEvents` 或后端事件路由时，应保持重复事件去重、replay gap 兜底和终态刷新行为。

## 项目 Reconcile 与 Repair

项目历史任务状态和当前产物完整性是两层概念：

- `latest_task_status` 记录历史任务终态。
- `reconciliation_status` 描述当前 metadata、状态文件和输出文件是否一致。
- `abnormal_completed` 表示曾有完成或部分完成记录，但当前关键输出缺失、不可读或格式不一致。
- `incomplete` 表示没有可靠完成记录且没有完成产物。
- `state_incomplete` 表示有产物但状态 metadata 不足。

Repair 规则：

- 后端生成 `repair_plan`，前端只提交 action id。
- 任何可能重新生成总结正文、调用 LLM 或覆盖既有输出的 repair 都必须要求用户确认。
- 项目修复以独立 `project_repair` 任务运行，不静默续跑原任务，也不重写原任务历史。
- 默认保留现有输出。覆盖行为必须显式披露。
- 首轮深度 repair 聚焦小说总结。文章总结、自定义总结、章节分割和雷点扫描若缺少安全实现，应返回 unsupported 或 blocked repair action。

后续扩展非小说 repair 时，应先明确安全输入、输出覆盖、LLM 成本、部分失败和用户确认语义，再新增 action。

## 配置恢复

本地配置按单用户本地应用处理。当前配置域包括：

- `api_configs.json`
- `user_settings.json`
- `chapter_patterns.json`

配置损坏或格式不符合预期时：

- 后端先尝试把原文件备份为同级 `.bak` 或非覆盖 `.bak.N`。
- 然后恢复安全默认值。
- API 响应应带上配置域、备份路径或备份失败原因 warning。
- 前端应在对应设置区域局部展示 warning。

当前不做配置 diff、损坏配置自动合并或恢复历史管理。若后续需要这些能力，应单独设计。

## 本地文件与输出目录边界

项目保留本地 picker 和打开输出目录能力，但边界是本地单用户应用，不是远程多人部署安全模型。

输出目录规则：

- 系统管理的输出目录在 `exports/` 下创建，并写入 ownership metadata。
- 删除项目时，只递归删除 ownership 与当前项目匹配的系统管理输出目录。
- 自定义输出目录、导入目录、缺失 ownership 或 ownership 不匹配的目录必须保留。
- 项目保存、任务启动和输出迁移等主动操作使用 strict 验证。无效自定义输出目录应返回明确错误，并保留前一次已保存输出目标。
- 历史项目、导入项目和项目详情读取使用 compat fallback。旧自定义路径无效时回退当前默认输出目录，并返回 warning。

本地能力规则：

- `open_directory` 只允许打开当前项目的有效输出目录。
- 后端应从项目 metadata 派生输出路径，不应接受任意本地路径作为通用打开 API。
- 文件选择器、目录选择器和系统 opener 在 headless、GUI 不可用或打包环境中可能失败，前端应在触发控件附近展示可操作错误。

## API 失败诊断

API 失败诊断用于本地排查：

- API key、Authorization 等敏感凭据必须脱敏。
- 非密钥输入、提示词和响应文本会作为本地诊断上下文保留。
- 诊断日志有清理和保留路径，但不是用户可见的通用日志管理功能。

若产品定位转向多人或远程部署，应重新设计诊断开关、字段截断、容量限制和 UI 披露。

## 后续维护约定

- 新增长任务 runner 时，必须沿用取消、暂停、`partial_failed` 和结构化 outcome 语义。
- 新增任务事件类型时，应通过统一事件发射路径，保留 `event_id`、持久化和 replay 行为。
- 新增配置域时，应复用 `.bak` 备份和配置域 warning 结构。
- 新增 OpenSpec change 并归档后，应检查 [spec_to_test_mapping.md](spec_to_test_mapping.md) 和 [archived_changes_index.md](archived_changes_index.md) 是否需要更新。
