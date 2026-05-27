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

### 已部分治理：实现变更历史多，但运行时决策文档不足

- 原始现象：归档 change 很多，说明近期功能演进密集；但缺少面向维护者的当前状态索引。
- 当前状态：已新增 `docs/stability_audit/` 系列文档，并把 `split-trigger-scan-page` 和 `harden-frontend-api-upload` 归档到 `openspec/changes/archive/`；`harden-chapter-splitting-boundaries` 已完成实现任务，等待归档。
- 剩余影响：README 维护者章节、运行时规则文档、spec-to-test 映射和 archived changes 索引仍未系统化。
- 当前风险级别：低到中。
- 建议：后续补 `docs/runtime_behavior_notes.md`、README “开发与验证”章节，以及 archived changes 摘要索引。

### 已澄清：部分 OpenSpec 契约与实现存在疑似漂移

- 现象：trigger scan 规格描述了 aggregation prompt/事件聚合能力，但代码实际没有调用 LLM 聚合。
- 证据：`workflow-prompt-composition` 提供 aggregation prompt 节点；后端只 render aggregation prompt 后执行本地 deterministic 聚合。
- 影响：提示词编辑器展示的能力不一定影响运行时。
- 原始风险级别：中。
- 当前状态：聚合提示词契约已澄清为 deterministic aggregation；`trigger-scan-page-modularity` 已同步为主规格，记录前端页面拆分边界和测试要求。
- 后续建议：如果要引入 LLM 聚合，另建 OpenSpec change 并明确成本、fallback、JSON schema、UI 披露和测试矩阵。

### 低风险：README 与当前代码大体一致，但缺少维护者视角

- 现象：README 说明了功能、技术栈和快速开始，但缺少测试命令、常见故障和变更流程。
- 证据：README 包含运行方式和配置说明，没有专门维护章节。
- 影响：开发者接手时不清楚应先跑哪些测试，哪些目录是运行时生成，哪些行为受 OpenSpec 约束。
- 风险级别：低到中。
- 建议：补充“开发与验证”章节，列出 `python -m pytest`、`npm run build` 和 OpenSpec 操作。

## 优化空间

- 建立 spec-to-test 映射索引。
- 为 archived change 提供索引摘要，减少翻阅成本。
- 将本次审计发现转化为后续小 change，而不是一次性大修。
- 归档后优先检查对应主规格是否已同步，例如 `trigger-scan-page-modularity` 已从 delta spec 落入 `openspec/specs/`。

## 验证

- 已读取当前 specs 和 archived changes 列表。
- `openspec validate --all` 通过，21 passed。
- 当前 active change：`harden-chapter-splitting-boundaries`，任务已完成，待归档。
