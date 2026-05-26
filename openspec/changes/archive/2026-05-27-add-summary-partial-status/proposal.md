## Why

稳定性审计发现，文章总结在单个 section 失败后仍可能继续生成最终总结，但用户界面和任务状态没有明确提示结果缺失；自定义总结虽然内容更少，也应避免把可用但不完整的结果伪装成完整成功。现在需要把“保留可用部分结果”和“明确标记 partial failure”收敛成统一、可验证的运行时契约。

## What Changes

- 为文章总结和自定义总结引入 summary partial status 语义：部分输入单元失败但仍产出可用结果时，保留结果并将任务终态标记为 `partial_failed`。
- 失败详情需要记录足够的用户可见信息，包括失败 section/输入单元、失败阶段或错误摘要，以及结果可能不完整的 warning。
- 文章总结默认继续用成功 section 生成最终总结，但最终结果必须带 partial warning；不会把缺 section 的结果标记为普通 `completed`。
- 自定义总结复用同一 partial result 表达方式；如果只有单个输入单元且失败后没有可用结果，仍按普通失败处理。
- 前端文章总结和自定义总结页面需要显示 `partial_failed` 状态、保留可用输出入口，并展示失败单元和 warning。
- 补充服务层和前端 focused tests，覆盖完整成功、部分失败、有结果 partial、无结果 failed、以及项目历史状态显示。

## Capabilities

### New Capabilities

- `summary-partial-status`: 定义文章总结和自定义总结在部分输入失败时如何保留可用结果、记录 warning，并暴露 `partial_failed`。

### Modified Capabilities

- `task-runtime-api`: 扩展 summary 类任务的终态契约，使 `partial_failed` 可用于文章总结和自定义总结，而不仅是雷点扫描。
- `webui-workbench`: 要求文章总结和自定义总结页面显示 partial failure 状态、warning、失败单元和可用结果。

## Impact

- 后端：`logic/article_summary_logic.py`、`logic/custom_summary_logic.py`、`webui_backend/workflow_services.py`、`webui_backend/task_runtime.py`、相关响应模型和项目 metadata 更新路径。
- 前端：文章总结/自定义总结页面、任务状态标签、项目历史状态展示、结果/warning 展示组件或 helper。
- 数据兼容：旧项目和旧任务可能没有 partial warning 或失败单元列表；读取时需要兼容为空。
- 测试：新增或扩展 `tests/test_article_summary_logic.py`、`tests/test_workflow_services.py`、任务运行时/项目历史相关测试，以及对应前端 Vitest focused tests。
