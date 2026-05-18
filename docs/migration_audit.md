# WebUI 迁移基线审计

变更：`migrate-to-webui-refactor`

## 旧入口启动检查

命令：

```powershell
python run_gui.py
```

结果：失败。

主要错误：

```text
ModuleNotFoundError: No module named 'python'
```

原因：`run_gui.py` 当前导入 `python.gui.main_app`，但仓库根目录下没有 `python/` 包目录；现有代码实际位于 `gui/`、`logic/`、`splitters/`。

## 核心模块检查

命令：

```powershell
python -m compileall gui logic splitters run_gui.py config.py
```

结果：失败。

发现：

- `gui/api_manager.py` 第 69 行附近存在字符串语法错误，编译时报 `SyntaxError: invalid character '。' (U+3002)`。
- 其他文件进入编译流程，但由于导入路径问题，实际导入仍不可用。

导入检查：

```powershell
python -c "import logic.orchestrator"
python -c "import logic.llm_api"
python -c "import logic.state_manager"
python -c "import splitters.default_strategy"
```

结果：均失败，主要原因是模块内部仍导入 `python.logic.*` 或 `python.config`。

## 当前依赖使用

`requirements.txt` 当前依赖：

- `chardet`：文本编码检测，`logic/chapter_splitter.py`、`logic/utils.py` 使用。
- `customtkinter`：旧桌面 GUI 使用，WebUI 稳定后移除。
- `requests`：当前扫描未发现直接使用点，后续确认是否可删除。
- `tiktoken`：Token 估算，`logic/utils.py`、`gui/custom_summary_manager.py` 使用。
- `httpx`：LLM API 调用，`logic/llm_api.py` 使用。
- `aiofiles`：异步文件读写，`logic/utils.py`、`logic/summarization_stages.py`、`logic/automated_super_summary.py` 使用。
- `PyYAML`：旧 GUI 状态和窗口配置，`run_gui.py`、`gui/ui_state_manager.py` 使用。

WebUI 迁移预计新增：

- `fastapi`
- `uvicorn`
- 前端工具链：React、Vite、TypeScript

## 用户数据位置

- `api_configs.json`：当前由 `gui/main_app.py` 设置在应用基础目录下，由 `gui/api_manager.py` 读写。
- `config.yaml`：旧 GUI 窗口位置、路径选择、模式和部分任务参数。
- `prompt_cache/`：全局提示词缓存，由 `logic/utils.py:get_global_prompt_cache_dir()` 管理。
- `.summarizer_cache/`：每个源文件夹下的任务缓存和产出目录。
- `task_id.txt`：位于 `.summarizer_cache/`，文件名来自 `config.py:TASK_ID_FILENAME`。

## 现有任务入口

- 小说总结：`logic/orchestrator.py:run_summarization_process`
- 文章总结：`logic/article_summary_logic.py:run_article_summary_process`
- 自定义总结：`logic/custom_summary_logic.py:run_custom_summary_process`
- 章节分割：`logic/chapter_splitter.py:split_novel_into_chapter_files`
- 获取模型：`logic/llm_api.py:fetch_available_models`

旧 GUI 触发点：

- `gui/event_handlers.py:start_summarization`
- `gui/event_handlers.py:start_splitting_process`
- `gui/event_handlers.py:_start_custom_summary_process`
- `gui/api_manager.py:update_model_list`

## 输出目录和文件命名规则

小说总结缓存根目录：

- `<源文件夹>/.summarizer_cache`

小说总结主要输出子目录：

- `1_小总结/剧情`
- `1_小总结/角色`
- `2_大总结/剧情`
- `2_大总结/角色`
- `3_超级总结/剧情_P1`
- `3_超级总结/剧情_P2`
- `3_超级总结/角色_P1`
- `3_超级总结/角色_P2`
- `4_终极总结/剧情_P1`
- `4_终极总结/剧情_P2`
- `4_终极总结/角色_P1`
- `4_终极总结/角色_P2`

文章总结输出子目录：

- `1_文章段落总结`
- `2_文章最终总结`

章节分割默认输出：

- 旧 GUI 在选择源文件后默认设置为源文件同级的 `splitted_chapters`。

迁移约束：

- WebUI 不应改变现有缓存和输出目录语义。
- 新服务需要集中处理中文路径、空格路径、长文件名和安全文件名。
