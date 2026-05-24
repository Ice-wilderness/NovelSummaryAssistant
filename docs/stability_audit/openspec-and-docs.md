# OpenSpec 与文档审计

## 模块职责

OpenSpec 记录能力契约、变更历史和任务清单；README 提供项目介绍、运行方式和功能说明；`docs/` 用于内部运行时和迁移文档。

## 关键入口

- `openspec/specs/`
- `openspec/changes/archive/`
- `openspec/changes/audit-project-stability-maintainability/`
- `README.md`
- `docs/`

## 发现

### 中风险：实现变更历史多，但运行时决策文档不足

- 现象：归档 change 很多，说明近期功能演进密集；但当前 `docs/` 目录在文件系统中没有已跟踪文档。
- 证据：仓库存在多个 archived OpenSpec change，`rg --files docs` 没有返回已跟踪文件。
- 影响：新接手者只能从 specs 和代码倒推实际运行规则，尤其是迁移、恢复、取消、输出目录优先级。
- 风险级别：中。
- 建议：把关键运行时规则沉淀到 `docs/runtime_behavior_notes.md` 或本次审计后续文档中。

### 中风险：部分 OpenSpec 契约与实现存在疑似漂移

- 现象：trigger scan 规格描述了 aggregation prompt/事件聚合能力，但代码实际没有调用 LLM 聚合。
- 证据：`workflow-prompt-composition` 提供 aggregation prompt 节点；后端只 render aggregation prompt 后执行本地 deterministic 聚合。
- 影响：提示词编辑器展示的能力不一定影响运行时。
- 风险级别：中。
- 建议：对每个 prompt node 标明是否实际参与 LLM 调用；修正 spec 或实现。

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

## 验证

- 已读取当前 specs 和 archived changes 列表。
- OpenSpec apply 状态在执行前为 `0/13`，当前任务正在逐项更新。
