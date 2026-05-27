# 章节分割与模式配置审计

## 模块职责

章节分割负责将整本 TXT 切分为单章文件，并向小说总结和雷点扫描提供章节粒度输入。模式配置负责保存可复用的正则策略。

## 关键入口

- `logic/chapter_splitter.py`
- `logic/chapter_boundaries.py`
- `splitters/default_strategy.py`
- `splitters/regex_strategy.py`
- `splitters/title_list_strategy.py`
- `logic/utils.py`（兼容门面）
- `logic/chapter_writing.py`
- `logic/chapter_naming.py`
- `webui_backend/pattern_config_service.py`
- `frontend/src/views/SplitterPage.tsx`
- `frontend/src/views/NovelSummaryPage.tsx`
- `frontend/src/components/splitting/SplitPreviewPanel.tsx`

## 发现

### 已治理：自定义正则没有运行时保护

- 现象：raw regex 会直接 `re.compile` 并对整本小说 `finditer`。
- 证据：`regex_strategy.compile_raw_pattern` 校验语法后直接编译，`process_chapters_with_regex` 对全文 `list(chapter_pattern.finditer(content))`。
- 影响：复杂或灾难性回溯正则可能卡住后端线程，影响本地服务可用性。
- 原始风险级别：中。
- 当前状态：`logic/chapter_boundaries.py` 已集中 raw regex 校验和预检，空表达式、语法错误、过长表达式、明显高风险嵌套重复和预检异常会在预览或实际分割前被拒绝。
- 验证：`tests/test_chapter_boundaries.py` 覆盖 accepted raw regex、无捕获组自动包裹、已有捕获组保留、语法错误、长度限制、高风险模式和空匹配预检。

### 已治理：分割错误被折叠为 `(False, 0)`

- 现象：`split_novel_into_chapter_files` 捕获所有异常并返回 `False, 0`。
- 证据：`logic/chapter_splitter.py` 顶层 `except Exception` 只写日志。
- 影响：API 层只能返回“分割失败”，丢失具体错误类型；用户和维护者排查成本高。
- 原始风险级别：中。
- 当前状态：章节边界解析和 raw regex 保护会抛出结构化 `ChapterSplitError`；预览 API、direct split、splitter task 和小说总结源文件分割会向用户暴露明确失败原因。兼容返回 `(False, 0)` 的旧调用仍保留，但新路径使用 `raise_on_error=True` 获取结构化原因。
- 验证：`tests/test_api_app.py` 覆盖预览无匹配、raw regex 高风险拒绝、direct split 失败和小说总结源文件分割失败；`tests/test_workflow_services.py` 覆盖 splitter task 失败原因。

### 已治理：预览和实际分割逻辑存在重复实现

- 现象：预览在 `chapter_splitter.preview_split` 中单独扫描章节，实际分割走 `process_chapters_with_regex` 和各 strategy。
- 证据：preview 有 `_preview_with_pattern`、`_preview_with_title_list`，实际写文件逻辑在 utils 和 splitters。
- 影响：预览结果和实际切分可能在边界条件下不一致。
- 原始风险级别：中。
- 当前状态：默认模式、simple/raw regex 模式和标题列表模式都通过共享章节边界解析结果生成预览和实际写文件；标题列表模式继续保留 unmatched preview items。
- 验证：`tests/test_chapter_boundaries.py` 覆盖默认、正则、标题列表、无匹配、行号和字数；`tests/test_chapter_granularity.py` 继续覆盖实际写出的单章文件。

### 低风险：模式配置损坏时自动重置

- 现象：`PatternConfigService` 读取 JSON 失败或不是 list 时直接写回默认预设。
- 证据：`_load_configs` 在 JSONDecodeError/OSError 时 `_save_configs(presets)`。
- 影响：用户配置文件损坏时可能丢失原内容，没有备份。
- 风险级别：低到中。
- 建议：重置前把损坏文件备份为 `.bak`，并向 UI 返回 warning。

## 优化空间

- 把“章节边界识别”和“章节文件写入”分离。
- 继续保持预览、direct split、小说总结源文件分割三条路径共用章节边界解析。
- 后续如扩展 raw regex 高级能力，优先补充预检样本和 focused tests，再放宽校验。
- `PatternConfigService` 配置损坏备份和 UI warning 可并入配置治理 change。

## 验证

- `python -m pytest` 通过；当前全量基线见 [tests-and-quality.md](tests-and-quality.md)。
- `tests/test_chapter_boundaries.py` 覆盖章节边界解析和 raw regex 保护。
- `tests/test_chapter_granularity.py` 覆盖章节写文件保持单章输出。
- `tests/test_project_workspace.py` 和 `tests/test_api_app.py` 覆盖小说总结源文件分割失败不清空既有 uploads。
- `npm run test` 通过，包含 `SplitterPage.test.tsx` 和 `NovelSummaryPage.test.tsx` 的分割失败展示与状态保留测试。
