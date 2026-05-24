# 章节分割与模式配置审计

## 模块职责

章节分割负责将整本 TXT 切分为单章文件，并向小说总结和雷点扫描提供章节粒度输入。模式配置负责保存可复用的正则策略。

## 关键入口

- `logic/chapter_splitter.py`
- `splitters/default_strategy.py`
- `splitters/regex_strategy.py`
- `splitters/title_list_strategy.py`
- `logic/utils.py`
- `webui_backend/pattern_config_service.py`
- `frontend/src/views/SplitterPage.tsx`
- `frontend/src/views/NovelSummaryPage.tsx`
- `frontend/src/components/splitting/SplitPreviewPanel.tsx`

## 发现

### 中风险：自定义正则没有运行时保护

- 现象：raw regex 会直接 `re.compile` 并对整本小说 `finditer`。
- 证据：`regex_strategy.compile_raw_pattern` 校验语法后直接编译，`process_chapters_with_regex` 对全文 `list(chapter_pattern.finditer(content))`。
- 影响：复杂或灾难性回溯正则可能卡住后端线程，影响本地服务可用性。
- 风险级别：中。
- 建议：对 raw regex 增加预检样本、长度限制和超时策略；至少在 UI 中提示高级风险。

### 中风险：分割错误被折叠为 `(False, 0)`

- 现象：`split_novel_into_chapter_files` 捕获所有异常并返回 `False, 0`。
- 证据：`logic/chapter_splitter.py` 顶层 `except Exception` 只写日志。
- 影响：API 层只能返回“分割失败”，丢失具体错误类型；用户和维护者排查成本高。
- 风险级别：中。
- 建议：保留用户友好的错误，同时把结构化错误原因返回给调用层。

### 中风险：预览和实际分割逻辑存在重复实现

- 现象：预览在 `chapter_splitter.preview_split` 中单独扫描章节，实际分割走 `process_chapters_with_regex` 和各 strategy。
- 证据：preview 有 `_preview_with_pattern`、`_preview_with_title_list`，实际写文件逻辑在 utils 和 splitters。
- 影响：预览结果和实际切分可能在边界条件下不一致。
- 风险级别：中。
- 建议：抽出共同的章节边界解析器，预览和写文件共享边界结果。

### 低风险：模式配置损坏时自动重置

- 现象：`PatternConfigService` 读取 JSON 失败或不是 list 时直接写回默认预设。
- 证据：`_load_configs` 在 JSONDecodeError/OSError 时 `_save_configs(presets)`。
- 影响：用户配置文件损坏时可能丢失原内容，没有备份。
- 风险级别：低到中。
- 建议：重置前把损坏文件备份为 `.bak`，并向 UI 返回 warning。

## 优化空间

- 把“章节边界识别”和“章节文件写入”分离。
- 为 raw regex 增加危险模式提示和定向测试。
- 为预览和实际分割的一致性建立测试矩阵。

## 验证

- `python -m pytest` 通过，包含章节粒度迁移和项目工作区相关分割测试。
