# 核心总结工作流审计

## 模块职责

核心总结逻辑位于 `logic/`，负责小说四阶段总结、文章总结、自定义总结、LLM 调用、提示词渲染、状态管理、进度事件和运行时输出。

## 关键入口

- `logic/orchestrator.py`
- `logic/summarization_stages.py`
- `logic/automated_super_summary.py`
- `logic/article_summary_logic.py`
- `logic/custom_summary_logic.py`
- `logic/llm_api.py`
- `logic/state_manager.py`
- `logic/utils.py`（兼容门面）
- `logic/summary_outputs.py`
- `logic/file_io.py`
- `logic/prompt_runtime.py`
- `logic/progress_events.py`
- `logic/text_extraction.py`
- `logic/chapter_naming.py`
- `logic/batching.py`
- `logic/api_logging.py`
- `logic/chapter_writing.py`
- `logic/prompts.py`

## 发现

### 已治理：取消会被核心 orchestrator 转换为失败

- 现象：小说总结主协调器捕获取消后返回 `False`。
- 证据：`logic/orchestrator.py` 的 `except asyncio.CancelledError` 返回 false；`webui_backend/workflow_services.py` 将 false 映射为 `"failed"`。
- 影响：取消、失败和异常被混在一起，前端状态、项目状态和用户判断都会受影响。
- 原始风险级别：高。
- 当前状态：小说总结取消已传播为 `CancelledError`，由 `TaskRuntime` 统一标记 `cancelled`，并补业务 runner 级取消测试。
- 后续建议：维护 orchestrator 时不要吞掉 `CancelledError`；如果需要清理资源，应清理后重新抛出。

### 已治理：文章/自定义总结也有取消语义漂移

- 现象：文章总结和自定义总结捕获取消后返回普通失败值或文本结果。
- 证据：`logic/article_summary_logic.py`、`logic/custom_summary_logic.py` 都捕获 `asyncio.CancelledError`；上层 runner 再把返回值解释成成功或失败。
- 影响：同一个“取消任务”动作在小说、文章、自定义总结之间可能显示不同终态，项目历史也难以统一分析。
- 原始风险级别：高。
- 当前状态：文章总结、自定义总结、章节分割和雷点扫描的用户取消已统一为 `cancelled` 终态，相关 workflow service 测试覆盖取消传播。
- 后续建议：新增长任务类型时沿用同一取消 contract。

### 中风险：阶段状态和文件存在性双重判断复杂

- 现象：`StateManager` 同时依赖 JSON 状态和输出文件是否存在来判断任务是否完成。
- 证据：`summarization_stages.py` 使用 `_completed_with_output`，`state_manager.py` 有输出文件存在性判断。
- 影响：手工删除输出、格式从 txt 切到 md、导入旧项目时，状态和文件可能不一致。
- 风险级别：中。
- 建议：统一定义“完成”的来源，导入/迁移时做一次明确 reconcile，并在项目进度中展示异常状态。

### 中风险：文章总结允许部分章节失败后继续生成终稿

- 现象：文章分段总结阶段单个 section 失败会记录错误并继续后续 section，最后仍可能基于已有 section 生成最终总结。
- 证据：`logic/article_summary_logic.py` 对 section 级异常使用 `continue`，最终阶段读取已生成的 section 文件。
- 影响：用户可能拿到看似完整、实则缺失部分输入的最终总结。
- 风险级别：中。
- 建议：在最终结果中明确 partial 状态、失败 section 列表和是否允许继续；默认策略应由配置或 UI 明示。

### 已部分治理：`llm_api.py` 失败日志可能包含完整输入内容

- 现象：API 调用失败日志包含 `input_messages`、`input_text` 和 `response_text`。
- 证据：`logic/llm_api.py` 失败路径把这些字段写入 `log_api_task_to_file`，只对 key/token 类字段脱敏。
- 影响：`.summarizer_cache/api_failures/` 可能保存长篇原文、用户提示词和模型输出，带来隐私和磁盘膨胀风险。
- 原始风险级别：中。
- 当前状态：API key、Authorization 等敏感凭据已脱敏，失败诊断日志已有清理/保留路径和测试；仍会保留非密钥输入/输出用于本地诊断。
- 后续建议：如果后续面向多人/远程部署或用户反馈磁盘增长，再增加诊断开关、字段截断和更明确的 UI 披露。

### 中风险：重试次数语义容易误解

- 现象：`call_llm_api` 使用 `for attempt in range(max_retries)`，即配置值代表总尝试次数，不是“失败后重试次数”。
- 证据：`ApiConfig.max_retries` 默认 3，UI 文案和字段名通常会让用户理解为“额外重试次数”。
- 影响：配置为 1 时没有额外重试；维护者后续改动时容易写错测试期望。
- 风险级别：中。
- 建议：重命名为 `max_attempts` 或改为 `range(max_retries + 1)` 并迁移语义。

### 已治理：工具模块职责过宽

- 现象：`logic/utils.py` 同时包含文件名清理、编码读取、提示词加载、排序、章节分割共享逻辑、日志落盘和批次分配。
- 证据：文件超过 1000 行，且被后端、分割、总结、雷点扫描共同依赖。
- 影响：低层工具改动容易影响多个工作流，测试定位成本高。
- 原始风险级别：低到中。
- 当前状态：`logic/utils.py` 已保留为兼容门面，相关实现已拆入 summary outputs、file IO、prompt runtime、progress events、text extraction、chapter naming、batching、API logging 和 chapter writing 等 focused modules。
- 后续建议：新增行为优先进入对应 focused module；只有某个模块继续膨胀时再小步拆分。

## 优化空间

- 维护已建立的取消/暂停语义 contract，新增 runner 必须复用。
- 为状态文件和输出文件 reconcile 建立独立服务。
- 为 LLM 调用日志增加隐私和容量策略。
- 为 partial success 建立统一展示方式，避免用户误读生成结果。
- 保持 `logic/utils.py` 作为兼容门面，避免重新加入业务实现。

## 验证

- `python -m pytest` 通过，现有测试覆盖 LLM 错误处理、状态恢复、小总结模式、文章总结和导入恢复等路径。
- `split-logic-utils` 后完整 `python -m pytest` 通过，217 passed。
- workflow service 测试覆盖小说、文章、自定义总结和雷点扫描的取消终态。
