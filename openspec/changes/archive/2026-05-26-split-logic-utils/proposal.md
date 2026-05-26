## Why

`logic/utils.py` 仍集中承载文件读写、提示词运行时、章节命名、API 诊断日志、批次分配和章节写入等低层职责，是当前稳定性审计中剩余的主要维护风险之一。先做无行为变化拆分，可以降低后续处理文章 partial success、章节分割一致性和诊断日志策略时的冲突面。

## What Changes

- 将 `logic/utils.py` 按职责逐步拆到更小的内部模块，建议边界包括 summary output path、file/text IO、prompt runtime、chapter naming/sorting、API logging、batch allocation 和 chapter writing helpers。
- 保留 `logic.utils` 作为兼容门面，现有 `from logic.utils import ...`、`from logic import utils` 和测试 mock 路径应继续可用。
- 保持现有小说总结、文章总结、自定义总结、章节分割、雷点扫描、WebUI 后端和测试行为不变。
- 每次只拆一个可独立验证的边界，并以现有 Python 测试保护回归。
- 不新增依赖，不改变输出目录结构、缓存目录结构、诊断日志格式、章节文件命名规则、批次分配语义或前端 API。

## Capabilities

### New Capabilities

- `logic-utils-modularity`: 定义 `logic/utils.py` 拆分后的内部模块边界、兼容门面要求和无行为变化验证要求。

### Modified Capabilities

- None.

## Impact

- 主要影响 `logic/utils.py`，并新增 `logic/` 下的 focused helper 模块或内部 package。
- 受影响调用面包括 `logic/orchestrator.py`、`logic/summarization_stages.py`、`logic/article_summary_logic.py`、`logic/custom_summary_logic.py`、`logic/llm_api.py`、`logic/state_manager.py`、`logic/trigger_scan/*`、`splitters/*`、`webui_backend/*` 和现有 Python 测试。
- 不影响 WebUI API URL、前端调用路径、OpenSpec 既有用户行为规格、持久化数据格式或运行时生成目录。
