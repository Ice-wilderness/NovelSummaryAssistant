## Why

章节分割现在同时承担预览、独立分割页写文件、小说总结页源文件入库等路径，但预览和实际分割存在重复实现，raw regex 也会直接对整本小说执行。下一轮稳定性修复应先把章节边界识别收敛为可复用、可验证、失败原因可见的契约，避免用户看到的预览和最终写出的章节不一致，也避免高风险正则卡住本地后端。

## What Changes

- 引入共享章节边界解析路径，预览和实际分割使用同一套章节边界结果。
- 对 raw regex 增加保守保护：明显高风险、过长、无法编译、预检失败或预检超限的模式 SHALL 被拒绝，并返回可操作错误。
- 将章节分割失败从笼统 `(False, 0)` 升级为结构化错误原因，API 和前端可展示用户可读提示。
- 保持独立分割页和小说总结页的既有成功流程不变；错误时不得写入不完整章节或污染项目 uploads。
- 不在本 change 中处理 `chapter_patterns.json` 损坏备份、配置恢复 warning 或更广泛的本地路径能力。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `split-preview`: 预览结果必须来自与实际分割一致的章节边界解析，并展示结构化错误。
- `chapter-pattern-config`: raw 正则配置在用于预览或实际分割前必须经过安全校验和预检，拒绝高风险模式。
- `chapter-processing-granularity`: 实际分割必须基于同一章节边界结果写出单章文件，并在失败时保留明确错误原因。
- `chapter-splitting-integration`: 小说总结页源文件分割失败时必须展示可操作错误，且不得修改项目章节列表。

## Impact

- 受影响代码：`logic/chapter_splitter.py`、`splitters/regex_strategy.py`、`splitters/default_strategy.py`、`splitters/title_list_strategy.py`、`logic/chapter_writing.py`、`webui_backend/routes/` 中的分割/预览路由、`frontend/src/views/SplitterPage.tsx`、`frontend/src/views/NovelSummaryPage.tsx`、`frontend/src/components/splitting/SplitPreviewPanel.tsx`。
- 受影响测试：章节分割、章节粒度、项目工作区、分割预览、小说总结页分割入口相关测试需要补充或调整。
- 不引入新第三方依赖；如需超时保护，优先使用可测试的预检/限制和隔离执行策略，不改变 package manager 或 lockfile。
