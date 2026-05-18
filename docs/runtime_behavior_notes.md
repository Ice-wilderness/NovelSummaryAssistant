# 任务运行行为记录

变更：`migrate-to-webui-refactor`

## 小说总结

- 入口：`logic.orchestrator.run_summarization_process`
- 暂停：通过 `pause_event` 和 `check_pause_async()` 在主要阶段之间生效。
- 取消：由外部取消 `asyncio.Task`，流程捕获 `asyncio.CancelledError` 并返回失败状态。
- 状态恢复：由 `StateManager` 管理 `.summarizer_cache/task_id.txt` 和 `state_<task_id>.json`。
- 本轮处理：移除了未使用的 `task_id` 入参；任务 ID 仍由 `StateManager` 负责创建和读取。

## 文章总结

- 入口：`logic.article_summary_logic.run_article_summary_process`
- 暂停：通过 `pause_event` 在每个文件和最终总结前检查。
- 取消：支持外部取消 `asyncio.Task`；同时保留 `stop_event` 兼容检查。
- 状态恢复：使用 `.summarizer_cache/article_summary_state.json` 记录已完成段落总结和最终总结状态。
- 本轮处理：修复了不存在的状态读写函数调用，并统一为异步入口。

## 自定义总结

- 入口：`logic.custom_summary_logic.run_custom_summary_process`
- 暂停：读取每个素材文件前检查 `pause_event`。
- 取消：支持外部取消 `asyncio.Task`。
- 后续迁移注意：当前旧 GUI 中仍存在一条更早的线程调用路径，WebUI 任务运行时接入时需要统一到异步入口。

## 章节分割

- 入口：`logic.chapter_splitter.split_novel_into_chapter_files`
- 暂停：当前同步拆分流程没有暂停点。
- 取消：当前同步拆分流程没有通用取消点，只能在任务运行时层面等待当前调用结束。
- 后续迁移注意：WebUI 接入时先作为短任务运行；如需要处理中超大文件，再拆出可取消的分段处理。
