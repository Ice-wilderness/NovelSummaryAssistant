# Archived Changes 索引

本文为 `openspec/changes/archive/` 的导航索引。归档目录中的 `proposal.md`、`design.md`、`tasks.md` 和 spec delta 仍是历史记录的权威来源；本文只提供主题、当前落点和快速查找入口。

## 近期稳定性与维护性变更

| 归档 change | 主题 | 当前落点 | 详细记录 |
| --- | --- | --- | --- |
| `2026-05-29-document-maintainer-runtime-rules` | 维护者指南、运行时规则、spec-to-test 映射和 archived changes 索引 | `openspec/specs/maintainer-runtime-documentation/spec.md`、`README.md`、`docs/runtime_behavior_notes.md`、`docs/spec_to_test_mapping.md`、`docs/archived_changes_index.md` | `openspec/changes/archive/2026-05-29-document-maintainer-runtime-rules/` |
| `2026-05-29-add-task-event-replay-heartbeat` | 任务事件 ID、SSE replay、heartbeat、事件日志保留 | `openspec/specs/task-runtime-api/spec.md`、`docs/runtime_behavior_notes.md` | `openspec/changes/archive/2026-05-29-add-task-event-replay-heartbeat/` |
| `2026-05-28-reconcile-project-state-outputs` | 项目状态/输出 reconcile、repair plan、project repair 任务 | `openspec/specs/managed-project-outputs/spec.md`、`openspec/specs/task-runtime-api/spec.md`、`openspec/specs/webui-workbench/spec.md` | `openspec/changes/archive/2026-05-28-reconcile-project-state-outputs/` |
| `2026-05-28-harden-local-config-path-boundaries` | 配置损坏备份、strict/compat 输出目录、本地路径能力边界 | `openspec/specs/configuration-management/spec.md`、`openspec/specs/managed-project-outputs/spec.md`、`docs/runtime_behavior_notes.md` | `openspec/changes/archive/2026-05-28-harden-local-config-path-boundaries/` |
| `2026-05-27-persist-task-terminal-summaries` | 任务终态摘要持久化、重启后 `interrupted` 状态 | `openspec/specs/task-runtime-api/spec.md`、`openspec/specs/webui-workbench/spec.md` | `openspec/changes/archive/2026-05-27-persist-task-terminal-summaries/` |
| `2026-05-27-harden-chapter-splitting-boundaries` | 章节边界共享解析、raw regex 保护、分割失败结构化原因 | `openspec/specs/split-preview/spec.md`、`openspec/specs/chapter-processing-granularity/spec.md`、`openspec/specs/chapter-pattern-config/spec.md`、`openspec/specs/chapter-splitting-integration/spec.md` | `openspec/changes/archive/2026-05-27-harden-chapter-splitting-boundaries/` |
| `2026-05-27-harden-frontend-api-upload` | 前端非 JSON 错误处理、上传大小预检、小说页分割任务 API client 统一 | `openspec/specs/webui-workbench/spec.md`、`openspec/specs/file-upload-workflow/spec.md` | `openspec/changes/archive/2026-05-27-harden-frontend-api-upload/` |
| `2026-05-27-add-summary-partial-status` | 文章/自定义总结 `partial_failed`、warning 和前端展示 | `openspec/specs/summary-partial-status/spec.md`、`openspec/specs/task-runtime-api/spec.md`、`openspec/specs/webui-workbench/spec.md` | `openspec/changes/archive/2026-05-27-add-summary-partial-status/` |
| `2026-05-26-split-logic-utils` | `logic/utils.py` 拆为 focused helper modules，保留兼容门面 | `openspec/specs/logic-utils-modularity/spec.md` | `openspec/changes/archive/2026-05-26-split-logic-utils/` |
| `2026-05-26-split-trigger-scan-page` | 雷点扫描页面拆分和前端测试基础 | `openspec/specs/trigger-scan-page-modularity/spec.md` | `openspec/changes/archive/2026-05-26-split-trigger-scan-page/` |
| `2026-05-26-split-project-workspace-services` | 项目工作区服务拆分，保留公开 facade | `openspec/specs/project-workspace-service-modularity/spec.md` | `openspec/changes/archive/2026-05-26-split-project-workspace-services/` |
| `2026-05-26-split-api-app-routes` | WebUI API 路由拆分和 route parity 保护 | `openspec/specs/webui-api-route-modularity/spec.md` | `openspec/changes/archive/2026-05-26-split-api-app-routes/` |
| `2026-05-26-sync-stability-backlog-status` | 稳定性审计 backlog 状态同步 | `openspec/specs/module-stability-audit-reports/spec.md`、`docs/stability_audit/` | `openspec/changes/archive/2026-05-26-sync-stability-backlog-status/` |
| `2026-05-25-address-stability-audit-priorities` | 首轮稳定性优先项：取消、雷点扫描状态、聚合契约、输出 ownership、诊断日志 | `docs/stability_audit/follow-up-backlog.md`、相关主规格 | `openspec/changes/archive/2026-05-25-address-stability-audit-priorities/` |
| `2026-05-24-audit-project-stability-maintainability` | 项目稳定性与可维护性审计报告 | `openspec/specs/module-stability-audit-reports/spec.md`、`docs/stability_audit/` | `openspec/changes/archive/2026-05-24-audit-project-stability-maintainability/` |

## 功能演进归档

| 归档 change | 主题 | 当前落点 | 详细记录 |
| --- | --- | --- | --- |
| `2026-05-24-add-chapter-splitting-to-summary-workflow` | 小说总结入口接入章节分割 | `openspec/specs/chapter-splitting-integration/spec.md`、`openspec/specs/split-preview/spec.md`、`openspec/specs/chapter-pattern-config/spec.md` | `openspec/changes/archive/2026-05-24-add-chapter-splitting-to-summary-workflow/` |
| `2026-05-23-add-trigger-scan` | 雷点扫描 workflow、结果、档案管理和 WebUI 集成 | `openspec/specs/trigger-scan-workflow/spec.md`、`openspec/specs/trigger-scan-results/spec.md`、`openspec/specs/trigger-profile-management/spec.md` | `openspec/changes/archive/2026-05-23-add-trigger-scan/` |
| `2026-05-23-show-stage-progress` | 阶段进度展示 | `openspec/specs/stage-progress-visualization/spec.md`、`openspec/specs/task-runtime-api/spec.md`、`openspec/specs/webui-workbench/spec.md` | `openspec/changes/archive/2026-05-23-show-stage-progress/` |
| `2026-05-23-remove-hybrid-scan-mode` | 移除 hybrid scan mode，澄清雷点扫描前置条件 | `openspec/specs/trigger-scan-workflow/spec.md`、`openspec/specs/chapter-processing-granularity/spec.md` | `openspec/changes/archive/2026-05-23-remove-hybrid-scan-mode/` |
| `2026-05-23-remove-skip-list` | 移除 skip list 相关结果行为 | `openspec/specs/trigger-scan-results/spec.md`、`openspec/specs/managed-project-outputs/spec.md` | `openspec/changes/archive/2026-05-23-remove-skip-list/` |
| `2026-05-21-improve-project-selector-and-status-updates` | 项目选择器、状态刷新和 managed output 改进 | `openspec/specs/webui-workbench/spec.md`、`openspec/specs/managed-project-outputs/spec.md`、`openspec/specs/task-runtime-api/spec.md` | `openspec/changes/archive/2026-05-21-improve-project-selector-and-status-updates/` |
| `2026-05-20-refactor-workflow-prompt-editor` | 提示词工作流编辑器和配置管理重构 | `openspec/specs/workflow-prompt-composition/spec.md`、`openspec/specs/configuration-management/spec.md`、`openspec/specs/webui-workbench/spec.md` | `openspec/changes/archive/2026-05-20-refactor-workflow-prompt-editor/` |
| `2026-05-20-replace-path-drag-with-file-upload-workflow` | 用上传工作流替代路径拖拽 | `openspec/specs/file-upload-workflow/spec.md`、`openspec/specs/managed-project-outputs/spec.md`、`openspec/specs/task-runtime-api/spec.md` | `openspec/changes/archive/2026-05-20-replace-path-drag-with-file-upload-workflow/` |
| `2026-05-19-migrate-to-webui-refactor` | 迁移到 WebUI 架构 | `openspec/specs/webui-workbench/spec.md`、`openspec/specs/task-runtime-api/spec.md`、`openspec/specs/configuration-management/spec.md` | `openspec/changes/archive/2026-05-19-migrate-to-webui-refactor/` |

## 维护约定

- 本索引只做导航，不复制归档 change 的完整设计或任务记录。
- 归档新 change 后，如果它影响运行时规则、主规格或测试映射，应同步更新本文和 [spec_to_test_mapping.md](spec_to_test_mapping.md)。
- 判断当前是否仍有未实现事项时，以 [stability_audit/00-overview.md](stability_audit/00-overview.md) 和 [stability_audit/follow-up-backlog.md](stability_audit/follow-up-backlog.md) 为准。
