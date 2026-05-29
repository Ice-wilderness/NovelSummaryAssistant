## Why

稳定性审计后的实现状态已经分散在 README、`docs/stability_audit/`、主规格和多个 archived changes 中，维护者需要在多处来回查找运行时规则、验证命令和规格到测试的关系。

现在补齐维护者文档、运行时规则说明、spec-to-test 映射和归档索引，可以降低后续接手、回归验证和归档追踪成本，并为后续 repair、前端交互测试和 LLM 聚合方案提供清晰边界。

## What Changes

- 在 README 中新增维护者视角的开发与验证说明，覆盖常用测试命令、OpenSpec 流程、运行时生成目录和常见故障入口。
- 新增运行时行为说明文档，集中记录任务终态、`partial_failed`、`interrupted`、SSE replay/heartbeat、repair、配置恢复和本地路径边界等当前规则。
- 新增 spec-to-test 映射文档，把高价值主规格与对应 Python/前端测试文件、验证命令关联起来。
- 新增 archived changes 索引文档，按主题概述近期归档变更、主规格落点和验证记录入口。
- 保持本次 change 为文档/维护性改动，不改变 API、运行时语义、前端交互或依赖。

## Capabilities

### New Capabilities

- `maintainer-runtime-documentation`: 维护者文档应描述当前运行时规则、验证入口、OpenSpec 维护流程、spec-to-test 映射和 archived changes 索引。

### Modified Capabilities

- None.

## Impact

- 影响文档：`README.md`、`docs/` 下新增维护者文档。
- 影响 OpenSpec：新增 `maintainer-runtime-documentation` 规格，用于约束维护者文档内容和更新要求。
- 不影响后端 API、前端运行时代码、数据格式、依赖或用户已有项目数据。
