## Why

部分 OpenAI 兼容接口会在流式响应中发送 `choices: []` 的用量或状态分块。当前解析器直接访问 `choices[0]`，会触发 `IndexError`、丢弃已接收内容并进行不必要的整次重试；非流式响应也存在相同的越界隐患。

## What Changes

- 流式解析在读取首个 choice 前校验响应结构，并跳过不携带候选内容的合法元数据分块。
- 对顶层 API 错误、缺失或无效的 `choices` 结构给出可诊断的受控错误，而不是泄漏 `IndexError`。
- 非流式解析同样防止空 `choices` 越界，并沿用现有重试与最终失败语义。
- 增加流式和非流式回归测试，覆盖空 choices、正常内容和错误响应。

## Capabilities

### New Capabilities

- `llm-api-response-parsing`: 定义 OpenAI 兼容聊天完成响应的安全解析、元数据分块容忍和无效响应错误处理行为。

### Modified Capabilities

无。

## Impact

- 主要涉及 `logic/llm_api.py` 的流式与非流式响应解析。
- 扩展 `tests/test_llm_api.py` 的模拟响应和回归用例。
- 不改变对外调用签名、API 配置格式或依赖项。
