## Context

`logic/utils.py` 目前包含 40 多个函数/类，覆盖 summary output 路径、阶段进度、API 诊断日志、文件读取、提示词加载、标签解析、章节名排序、章节批次分配、章节写入和最终总结路径等职责。调用面横跨 `logic/` 核心总结、`logic/trigger_scan/`、`splitters/`、`webui_backend/` 和现有测试。

本 change 是无行为变化重构。目标不是修复章节分割、文章 partial success 或诊断日志策略，而是先把低层工具边界拆清楚，让后续行为修复可以落在更小、更可测的模块中。

## Goals / Non-Goals

**Goals:**

- 将 `logic/utils.py` 中可独立理解和验证的职责拆到 focused modules。
- 保留 `logic.utils` 作为稳定兼容门面，避免一次性迁移所有调用点和 mock 路径。
- 保持文件名清理、输出路径查找、提示词加载、API 诊断日志、章节排序、批次分配和章节写入行为不变。
- 每个拆分步骤都能通过窄范围测试验证，最后再运行完整 Python 测试。
- 清理本次拆分造成的未使用 import、重复 helper 和死代码。

**Non-Goals:**

- 不改变用户可见功能、WebUI API、前端行为或 OpenSpec 既有业务规格。
- 不修复文章总结 partial success、状态文件与输出文件 reconcile、raw regex 超时保护或预览/实际分割一致性。
- 不改变 `.summarizer_cache/`、API failure logs、prompt cache、summary outputs 或章节文件的目录/文件格式。
- 不新增依赖，不引入新的服务容器或插件机制。
- 不把 `logic/utils.py` 替换为同名 package，因为这会改变 Python import 解析并增加兼容风险。

## Decisions

1. 保留 `logic/utils.py` 作为兼容门面。

   新模块承载实现，`logic/utils.py` re-export 现有公开符号。现有调用方可以继续使用 `from logic.utils import ...` 或 `from logic import utils`，现有测试里的 `mock.patch("logic.utils...")` 默认继续工作。

   备选方案是直接迁移所有调用点到新模块。该方式能更快暴露真实边界，但会让 diff 覆盖大量文件，增加无行为重构的回归面。

2. 使用平铺 focused modules，而不是新增 `logic/utils/` package。

   `logic/utils.py` 已存在，新增同名 package 会带来导入歧义。实现时优先新增平铺模块，例如 `logic/summary_outputs.py`、`logic/file_io.py`、`logic/prompt_runtime.py`、`logic/chapter_naming.py`、`logic/api_logging.py`、`logic/batching.py`、`logic/chapter_writing.py`。最终命名以代码依赖和最小 diff 为准。

   备选方案是新增一个 `logic/support/` 包集中存放。它能减少 `logic/` 根目录文件数量，但会在当前小项目里增加一层导航成本。

3. 先拆纯函数和低状态 helper，再拆带异步锁、日志和写文件副作用的边界。

   建议顺序是 summary output helpers、filename/chapter sort helpers、batch allocation、file/prompt helpers、API logging、chapter writing。每一步只移动一类职责，运行对应测试后再继续。

   备选方案是按代码顺序机械拆分。它的 diff 更简单，但模块边界不一定反映真实职责，后续维护收益较低。

4. 以行为测试为主，必要时补 focused tests。

   本次拆分不应把测试绑定到过细实现。优先运行现有 `tests/test_utils.py`、`tests/test_llm_api.py`、`tests/test_chapter_granularity.py`、`tests/test_article_summary_logic.py`、`tests/test_state_manager_resume.py` 和相关 trigger scan/workflow tests。只有当新模块边界本身有风险，例如 re-export、日志清理、章节批次命名或章节写入边界，才补小型定向测试。

   备选方案是为每个新模块补完整单测。它会提高局部覆盖，但在无行为拆分阶段容易制造大量结构耦合测试。

## Risks / Trade-offs

- 公开导入路径漂移 -> `logic/utils.py` 保留 re-export，并运行现有 import-heavy 测试。
- `mock.patch("logic.utils...")` 失效 -> 对被测试 patch 的符号保留门面绑定，必要时调整测试到更稳定的行为入口。
- 循环导入 -> 新模块只依赖标准库、常量和更低层 helper；避免新模块反向导入 `logic.utils`。
- API 诊断日志行为漂移 -> 移动后运行 LLM API failure log、清理和脱敏相关测试。
- 章节命名/排序/写入边界漂移 -> 移动后运行章节粒度、章节分割、state resume 和 summary workflow 相关测试。
- 拆分过细导致导航成本上升 -> 按真实职责聚合函数，不为单个 helper 单独建文件。

## Migration Plan

1. 建立基线：记录 `logic/utils.py` 当前公开符号和调用面，运行最相关的 `tests/test_utils.py`。
2. 拆出纯 summary output、filename、chapter sorting 和 batch allocation helper，通过 `logic/utils.py` re-export。
3. 拆出 file IO、prompt runtime、tag extraction 和 pause/progress logging helper，保持现有调用路径。
4. 拆出 API logging 与 failure log cleanup，确认异步锁、脱敏和保留策略不变。
5. 拆出 chapter writing/splitting-adjacent helper，确认 `splitters/*` 和总结工作流行为不变。
6. 清理本次产生的未使用 import 和重复 helper，运行完整 `python -m pytest`。

回退策略是按功能块提交逐个 revert。由于不改变数据格式、API contract 或输出目录布局，不需要运行时数据迁移。

## Open Questions

- 新模块最终命名在实现时以依赖关系和最小 diff 为准；默认采用平铺 `logic/*.py`。
- 如果拆分过程中发现某个 helper 本身存在行为缺陷，默认记录为后续 change，不在本 change 中顺手修复，除非它阻塞无行为拆分。
