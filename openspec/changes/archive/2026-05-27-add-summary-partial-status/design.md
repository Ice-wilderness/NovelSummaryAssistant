## Context

文章总结当前会逐个 `.txt` 文件生成 section summary；单个 section 失败时只记录日志并继续，最终阶段仍可能使用已有 section summary 生成最终总结。这个行为本身可以保留可用结果，但现在缺少失败 section 列表、partial warning 和 `partial_failed` 任务终态，用户容易把缺失部分的总结当成完整结果。

自定义总结当前会读取多个素材文件并合并后调用一次 LLM。读取单个素材失败时会继续处理其他文件，但只要最终 LLM 调用成功，任务仍表现为普通成功。它没有文章总结那样的多段 LLM 阶段，但同样需要在部分素材缺失时显式提示。

现有 `TaskRuntime` 的公开状态类型和前端类型已经出现 `partial_failed` 语义，但后端 `TaskStatus` 和 runner 返回值仍主要围绕字符串结果、`failed` 字符串和异常处理。为了避免一次性重写所有任务 runner，本次应保持向后兼容，只给需要结构化状态的 summary runner 增加清晰出口。

## Goals / Non-Goals

**Goals:**

- 文章总结 section 级失败后，若至少有可用 section summary 且最终总结成功生成，任务终态为 `partial_failed`，最终结果保留并带 warning。
- 自定义总结素材读取部分失败后，若至少有可用素材且最终 LLM 调用成功，任务终态为 `partial_failed`，生成结果保留并带 warning。
- 当没有任何可用 section/material，或最终 LLM 调用失败且没有可交付结果时，任务仍为 `failed`。
- `partial_failed` 任务记录应包含用户可见 warning 和失败单元列表，前端无需解析日志即可展示。
- 前端文章总结和自定义总结页面、全局任务状态和项目历史应显示 `partial_failed`，并保留访问可用结果的入口。
- 新增 focused tests 覆盖成功、partial 和 failed 的边界。

**Non-Goals:**

- 不新增“遇到 section 失败时停止/继续”的用户配置项；本次固定采用继续生成并标记 partial 的方案 A。
- 不处理小说总结阶段状态与输出文件 reconcile。
- 不改动雷点扫描 partial report 语义。
- 不引入新的外部依赖或新的上传/流式处理机制。
- 不重新设计任务持久化、SSE replay 或后端重启恢复。

## Decisions

### 1. 采用结构化 task outcome，保持旧 runner 兼容

新增一个轻量 `TaskRunOutcome` 或等价结构，包含 `status`、`result_summary`、`error`、`warnings` 和可选 `data`。`TaskRuntime` 接受旧的 `str | None` runner 返回值，也接受新的结构化 outcome。

旧 runner 返回字符串时沿用当前规则：`"failed"` 或 `ERROR:` 表示失败，其他字符串表示成功。summary runner 返回结构化 outcome 时，`TaskRuntime` 按 outcome.status 设置 `success`、`failed` 或 `partial_failed`，并把 warnings/data 写入 `TaskRecord` 和事件。

替代方案是在 runner 内直接修改 `TaskRecord.status`。这会把运行时终态控制分散到业务逻辑里，不采用。

### 2. 文章总结记录 failed sections 并继续最终总结

文章 section 阶段捕获单个文件异常时，不只写日志，还把失败文件名、阶段、错误摘要记录到本次运行状态。section 阶段结束后：

- 全部 section 成功且最终总结成功：返回 success。
- 部分 section 失败、至少一个 section summary 可用、最终总结成功：返回 partial outcome。
- 全部 section 失败或没有 section summary：返回 failed。
- 最终总结失败：返回 failed，因为没有新的可交付最终结果。

失败 section 信息应同时写入 `article_summary_state.json` 或相邻 summary status 文件，便于刷新项目后仍可提示。最终总结文件本身可保持原内容，但 UI 和 task metadata 必须显示 warning。

替代方案是遇到第一个 section 失败就停止。它会丢失长任务中已经生成的可用内容，不符合本次确认的方案 A。

### 3. 自定义总结把素材读取失败视为 partial 输入

自定义总结读取多个素材时记录 failed materials。若至少一个素材读取成功且最终 LLM 调用成功，则：

- 没有素材读取失败：返回 success。
- 存在素材读取失败：返回 partial outcome，保留生成文本，并展示失败素材列表。

若所有素材都读取失败，或最终 LLM 调用失败没有生成结果，则返回 failed。由于自定义总结只有一次 LLM 输出，本次不尝试在最终 LLM 失败后交付部分模型结果。

### 4. 前端展示使用结构化 warnings，不解析日志

API 返回的 `TaskRecord` 应包含 warnings 和可选 result data。文章总结和自定义总结页面显示：

- 状态标签 `partial_failed`。
- “已保留可用结果，但部分输入失败”的 warning。
- 失败 section/material 列表，列表过长时可截断展示。
- 当前已有的结果摘要或输出目录入口。

全局状态栏和历史项目状态继续复用现有 partial 状态样式。旧项目没有 warnings 时不显示空 warning。

### 5. 验证以服务层和 focused frontend tests 为主

先扩展 article/custom 逻辑单测，确认 partial result 数据；再扩展 workflow service/task runtime 测试，确认结构化 outcome 被转换为 `partial_failed`；最后补前端页面或 helper 测试，确认 warning 和状态可见。

## Risks / Trade-offs

- 结构化 outcome 会触及 `TaskRuntime` 公共模型 → 通过兼容旧字符串返回值降低改动面，并用 task runtime 单测保护旧 runner 行为。
- 旧项目缺少 warning/result data → 读取时默认空列表和空对象，不阻塞历史项目展示。
- 文章总结最终文件本身不包含 warning → UI 和 task metadata 会显示 warning；如后续需要导出自带声明，可另开文档/输出格式 change。
- 自定义总结的 partial 只覆盖素材读取失败 → LLM 最终调用失败仍无可用结果，因此保持 failed，避免假装有部分模型输出。
- `partial_failed` 扩展到 summary 类任务后，前端状态映射必须保持通用 → 使用现有 partial 样式并补 focused tests。

## Migration Plan

1. 为 `TaskRecord` 增加 warnings/result data 的兼容字段，旧响应默认为空。
2. 为 `TaskRuntime` 增加 `partial_failed` 终态和结构化 outcome 归一化，保持字符串 runner 行为不变。
3. 更新文章总结和自定义总结逻辑，记录失败单元并返回结构化结果。
4. 更新 workflow service runner，把 summary 结果映射到 `TaskRunOutcome`。
5. 更新前端类型和文章/自定义页面展示。
6. 先运行 focused Python/Vitest 测试，再运行 `python -m pytest`、`npm run test` 和 `npm run build`。

## Open Questions

- 是否需要把 warning 写入最终总结正文顶部。本次默认不写入正文，只通过任务记录和前端展示提示。
