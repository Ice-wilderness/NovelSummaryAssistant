# OpenSpec 与文档审计

## 模块职责

OpenSpec 记录能力契约、变更历史和任务清单；README 提供项目介绍、运行方式和功能说明；`docs/` 用于内部运行时和迁移文档。

## 关键入口

- `openspec/specs/`
- `openspec/changes/archive/`
- `openspec/specs/trigger-scan-page-modularity/spec.md`
- `docs/stability_audit/`
- `README.md`
- `docs/`

## 发现

### 已治理：实现变更历史多，但运行时决策文档不足

- 原始现象：归档 change 很多，说明近期功能演进密集；但缺少面向维护者的当前状态索引。
- 当前状态：已新增 `docs/stability_audit/` 系列文档；README 已补维护者指南；运行时规则、spec-to-test 映射和 archived changes 索引已分别沉淀到 `docs/runtime_behavior_notes.md`、`docs/spec_to_test_mapping.md` 和 `docs/archived_changes_index.md`。
- 剩余影响：这些文档后续需要随新 change、归档和测试覆盖变化持续维护。
- 当前风险级别：低。
- 建议：归档新 change 时同步检查 README、运行时规则、spec-to-test 映射和 archived changes 索引是否需要更新。

### 已澄清：部分 OpenSpec 契约与实现存在疑似漂移

- 现象：trigger scan 规格描述了 aggregation prompt/事件聚合能力，但代码实际没有调用 LLM 聚合。
- 证据：`workflow-prompt-composition` 提供 aggregation prompt 节点；后端只 render aggregation prompt 后执行本地 deterministic 聚合。
- 影响：提示词编辑器展示的能力不一定影响运行时。
- 原始风险级别：中。
- 当前状态：聚合提示词契约已澄清为 deterministic aggregation；`trigger-scan-page-modularity` 已同步为主规格，记录前端页面拆分边界和测试要求。
- 后续建议：如果要引入 LLM 聚合，另建 OpenSpec change 并明确成本、fallback、JSON schema、UI 披露和测试矩阵。

### 已治理：README 与当前代码大体一致，但缺少维护者视角

- 现象：README 说明了功能、技术栈和快速开始，但缺少测试命令、常见故障和变更流程。
- 当前状态：README 已新增维护者指南，列出后端、前端、构建和 OpenSpec 验证命令，并链接运行时规则、spec-to-test 映射和 archived changes 索引。
- 当前风险级别：低。
- 建议：新增维护者入口或验证流程时继续保持 README 只放高频入口，详细规则放在 `docs/`。

## 优化空间

- 持续维护 spec-to-test 映射索引。
- 持续维护 archived changes 索引摘要，减少翻阅成本。
- 将本次审计发现转化为后续小 change，而不是一次性大修。
- 归档后优先检查对应主规格是否已同步，例如 `trigger-scan-page-modularity` 已从 delta spec 落入 `openspec/specs/`。

## 验证

- 已读取当前 specs 和 archived changes 列表。
- `openspec validate --all` 通过，21 passed。
- 当前 active change：`document-maintainer-runtime-rules` 已完成全部任务，等待归档；最近归档：`openspec/changes/archive/2026-05-29-add-task-event-replay-heartbeat/`。
