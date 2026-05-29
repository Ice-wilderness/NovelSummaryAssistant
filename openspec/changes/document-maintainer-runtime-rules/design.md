## Context

项目已经完成多轮稳定性治理：任务终态、事件回放、项目 reconcile/repair、配置和本地路径边界、前端 focused tests 等规则均已落地。当前状态主要记录在 `docs/stability_audit/`、README、主规格和 archived changes 中，维护者需要跨多个入口拼合“现在应该怎么运行、验证和演进”。

本次 change 是文档型维护改动，目标是把当前运行时契约和维护流程整理成稳定入口。它不改变代码路径、不改变用户可见交互，也不引入新的测试框架或自动化。

## Goals / Non-Goals

**Goals:**

- 在 README 中提供维护者入口，说明本地开发、验证命令、OpenSpec 流程、运行时目录和常见故障排查入口。
- 新增运行时规则文档，集中说明任务状态、SSE replay/heartbeat、`partial_failed`、`interrupted`、repair、配置恢复和本地路径能力边界。
- 新增 spec-to-test 映射，帮助维护者从高价值规格找到对应测试和推荐验证命令。
- 新增 archived changes 索引，按主题记录近期归档变更、对应主规格和关键验证入口。
- 让这些文档成为后续 change 归档和规格维护时可更新的约定。

**Non-Goals:**

- 不扩展非小说工作流 repair 行为。
- 不实现 LLM trigger aggregation。
- 不新增 Playwright、浏览器 E2E 或其他测试依赖。
- 不改变 API、任务状态、文件布局、配置格式或前端交互。

## Decisions

1. 使用顶层 `docs/` 文档承载维护者材料。
   - 选择：新增 `docs/runtime_behavior_notes.md`、`docs/spec_to_test_mapping.md`、`docs/archived_changes_index.md`。
   - 理由：这些内容跨模块、跨规格，不属于单一审计报告；放在 `docs/` 顶层更容易从 README 链接。
   - 备选：放入 `docs/stability_audit/`。该目录更适合保存审计发现快照，不适合作为长期维护入口。

2. README 只放入口和高频命令，详细规则放入 docs。
   - 选择：README 增加维护者章节，链接到新增文档。
   - 理由：README 应保持可扫读；运行时状态和映射表会持续增长，单独文档更利于维护。
   - 备选：把所有内容写入 README。这样会让 README 膨胀，并增加用户快速开始内容的噪音。

3. spec-to-test 映射以人工维护的清单为主。
   - 选择：记录高价值规格、关键 requirement 主题、测试文件和推荐验证命令。
   - 理由：当前测试与规格关系来自行为覆盖和命名约定，人工清单能在不引入工具链的情况下立即降低漂移风险。
   - 备选：生成自动映射。现有测试没有统一元数据，自动化会扩大本次 change 范围。

4. archived changes 索引按主题聚合，而不是复制每个 change 的全文。
   - 选择：记录 change 名称、主题、落入的主规格、关键验证入口和备注。
   - 理由：索引用于导航，细节仍以 archived change 的 `proposal.md`、`design.md`、`tasks.md` 为准。
   - 备选：为每个归档 change 写完整摘要。成本更高，也容易和源文档再次漂移。

## Risks / Trade-offs

- 文档可能随实现继续漂移 -> 在 tasks 中加入 OpenSpec 校验和链接检查，并在文档中明确后续 change 归档时同步更新映射/索引。
- spec-to-test 映射无法证明完整覆盖 -> 明确它是维护导航，不替代测试执行；优先覆盖高价值规格和稳定性审计后的重点路径。
- archived changes 索引过细会增加维护成本 -> 只记录近期稳定性相关和高价值归档入口，避免复刻归档目录。
- README 内容变多影响新用户阅读 -> README 仅加入维护者入口，详细内容放到单独 docs。
