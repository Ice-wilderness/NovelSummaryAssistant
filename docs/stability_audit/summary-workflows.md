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
- `logic/utils.py`
- `logic/prompts.py`

## 发现

### 高风险：取消会被核心 orchestrator 转换为失败

- 现象：小说总结主协调器捕获取消后返回 `False`。
- 证据：`logic/orchestrator.py` 的 `except asyncio.CancelledError` 返回 false；`webui_backend/workflow_services.py` 将 false 映射为 `"failed"`。
- 影响：取消、失败和异常被混在一起，前端状态、项目状态和用户判断都会受影响。
- 风险级别：高。
- 建议：取消应重新抛出，让 `TaskRuntime` 统一标记 cancelled；同时保留日志事件说明。

### 高风险：文章/自定义总结也有取消语义漂移

- 现象：文章总结和自定义总结捕获取消后返回普通失败值或文本结果。
- 证据：`logic/article_summary_logic.py`、`logic/custom_summary_logic.py` 都捕获 `asyncio.CancelledError`；上层 runner 再把返回值解释成成功或失败。
- 影响：同一个“取消任务”动作在小说、文章、自定义总结之间可能显示不同终态，项目历史也难以统一分析。
- 风险级别：高。
- 建议：所有业务 runner 统一让 `CancelledError` 传播到 `TaskRuntime`，并补小说、文章、自定义总结三条取消测试。

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

### 中风险：精细流程自动超级总结会生成重复的分批 P1

- 现象：精细流程开启后，自动超级总结会把所有大总结按 `super_summary_threshold` 切成多个 `auto_batch_*`，每个批次都分别生成剧情 P1/P2 和角色 P1/P2。剧情 P1 的目标是“世界观与核心设定总览”，多批次输入常会反复包含同一套世界观、力量体系和核心设定，导致多个 `auto_batch_*_plot_p1` 输出高度相似。
- 证据：`logic/automated_super_summary.py` 的 `run_automated_super_summary_stage` 对所有大总结文件调用 `_create_batches`，随后 `_process_super_summary_batch_for_api` 对每个批次都调用 `prompt_super_plot_p1`。UI 文案将 `super_summary_threshold` 描述为“达到多少个大总结后触发超级总结阶段”，但精细流程中实际表现更接近“每多少个大总结生成一个超级总结批次”。
- 影响：用户会看到多个几乎重复的剧情 P1 文件，误以为流程重复或输入错位；终极总结还需要再处理这些重复材料，增加 token 成本和去重压力。
- 风险级别：中。
- 建议：后续直接调整精细流程的超级总结设计：把 `auto_batch_*` 产物定位为中间分片摘要，最终用户可见的超级剧情 P1/P2、超级角色 P1/P2 应在分片完成后再统一合并生成一份规范结果；如果上下文允许，也可以让 P1 直接基于全部剧情大总结只生成一次，而不是每个 auto batch 都生成一次。避免仅靠提示词要求“本批次新增内容”来修补流程语义。

### 中风险：`llm_api.py` 失败日志可能包含完整输入内容

- 现象：API 调用失败日志包含 `input_messages`、`input_text` 和 `response_text`。
- 证据：`logic/llm_api.py` 失败路径把这些字段写入 `log_api_task_to_file`，只对 key/token 类字段脱敏。
- 影响：`.summarizer_cache/api_failures/` 可能保存长篇原文、用户提示词和模型输出，带来隐私和磁盘膨胀风险。
- 风险级别：中。
- 建议：默认截断输入/响应，提供诊断开关；报告里只记录必要片段和哈希。

### 中风险：重试次数语义容易误解

- 现象：`call_llm_api` 使用 `for attempt in range(max_retries)`，即配置值代表总尝试次数，不是“失败后重试次数”。
- 证据：`ApiConfig.max_retries` 默认 3，UI 文案和字段名通常会让用户理解为“额外重试次数”。
- 影响：配置为 1 时没有额外重试；维护者后续改动时容易写错测试期望。
- 风险级别：中。
- 建议：重命名为 `max_attempts` 或改为 `range(max_retries + 1)` 并迁移语义。

### 低风险：工具模块职责过宽

- 现象：`logic/utils.py` 同时包含文件名清理、编码读取、提示词加载、排序、章节分割共享逻辑、日志落盘和批次分配。
- 证据：文件超过 1000 行，且被后端、分割、总结、雷点扫描共同依赖。
- 影响：低层工具改动容易影响多个工作流，测试定位成本高。
- 风险级别：低到中。
- 建议：逐步拆分为 `file_utils`、`prompt_runtime`、`chapter_naming`、`api_logging` 等模块。

## 优化空间

- 为取消/暂停语义建立统一 contract。
- 为状态文件和输出文件 reconcile 建立独立服务。
- 为 LLM 调用日志增加隐私和容量策略。
- 为 partial success 建立统一展示方式，避免用户误读生成结果。
- 重构精细流程的自动超级总结，让分批处理与最终用户可见产物分层，避免多个 P1/P2 输出语义重复。

## 验证

- `python -m pytest` 通过，现有测试覆盖 LLM 错误处理、状态恢复、小总结模式、文章总结和导入恢复等路径。
