## Purpose

确保小说总结工作流能够安全解析 OpenAI 兼容聊天完成响应，容忍合法的流式元数据分块，并把无效响应转换为可诊断、可按既有策略重试的失败。

## ADDED Requirements

### Requirement: 流式空候选分块不得中断内容生成
系统 MUST 将 `choices` 为空列表且不包含 API 错误的流式 JSON 分块视为非内容元数据，并继续处理同一响应中的后续分块。

#### Scenario: 内容分块之间出现空 choices
- **WHEN** 流式响应依次提供内容分块、`choices: []` 分块、后续内容分块和结束标记
- **THEN** 系统 MUST 按顺序合并全部内容片段并成功返回
- **AND** 系统 MUST NOT 因空列表访问而重试整个请求

#### Scenario: 流中只有空 choices 分块
- **WHEN** 流式响应结束前仅提供 `choices: []` 分块而没有任何内容
- **THEN** 系统 MUST 按既有空响应规则重试或报告最终失败
- **AND** 报告的失败 MUST NOT 是未处理的 `IndexError`

### Requirement: API 错误分块必须可诊断
系统 MUST 在解析候选内容前识别响应顶层的非空 `error`，保留可用的上游错误消息，并按既有 API 重试策略处理该次失败。

#### Scenario: 流式响应返回错误对象
- **WHEN** HTTP 成功响应中的流式 JSON 分块包含非空顶层 `error` 对象
- **THEN** 系统 MUST 将该分块作为 API 失败处理
- **AND** 诊断信息 MUST 包含上游提供的错误消息（如存在）

#### Scenario: 非流式响应返回非对象错误值
- **WHEN** 非流式响应包含非空顶层 `error`，且该值不是 JSON 对象
- **THEN** 系统 MUST 将该错误值转换为可诊断文本并按既有策略处理失败
- **AND** 系统 MUST NOT 泄漏响应解析器自身的属性访问异常

### Requirement: 候选响应结构必须安全校验
系统 MUST 在访问首个候选项前校验顶层响应、`choices` 集合和首个候选项的结构；无法作为合法元数据处理的缺失或无效结构 MUST 转换为受控的响应格式错误。

#### Scenario: 非流式响应包含空 choices
- **WHEN** 非流式聊天完成响应包含 `choices: []`
- **THEN** 系统 MUST 将该次响应报告为受控的 API 响应格式失败并应用既有重试策略
- **AND** 系统 MUST NOT 抛出未处理的 `IndexError`

#### Scenario: choices 不是列表
- **WHEN** 聊天完成响应中的 `choices` 存在但不是列表
- **THEN** 系统 MUST 报告可诊断的响应格式错误
- **AND** 系统 MUST NOT 抛出未处理的类型或属性访问异常

#### Scenario: 首个 choice 不是对象
- **WHEN** `choices` 是非空列表但首个元素不是 JSON 对象
- **THEN** 系统 MUST 报告可诊断的响应格式错误
- **AND** 系统 MUST NOT 尝试从该元素读取内容字段

### Requirement: 既有有效响应行为保持不变
系统 MUST 继续从首个候选项提取内容，并将成功内容交由既有的空内容、格式、错误短语和最少输出字符数校验处理。

#### Scenario: 标准流式响应成功
- **WHEN** 流式响应包含结构有效的首个 choice 和字符串内容片段
- **THEN** 系统 MUST 按接收顺序拼接内容并返回现有格式的成功结果

#### Scenario: 标准非流式响应成功
- **WHEN** 非流式响应包含结构有效的首个 choice、message 和字符串 content
- **THEN** 系统 MUST 返回现有格式的成功结果
