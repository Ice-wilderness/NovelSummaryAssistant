## Context

当前章节分割有三条主要路径：预览 API、独立分割页写入导出目录、小说总结页源文件分割后写入项目 `inputs`。默认模式和 raw/simple 正则最终主要依赖 `process_chapters_with_regex` 写文件，而预览在 `logic/chapter_splitter.py` 中单独实现 `_preview_with_pattern` 和 `_preview_with_title_list`。标题列表实际分割还使用 `re.split` 的独立流程。

这导致两个稳定性问题：第一，预览和实际分割可能在边界、标题、字数和未匹配处理上漂移；第二，raw regex 目前会直接编译并对整本小说 `finditer`，明显高风险模式可能让本地后端长时间不可用。失败路径也多被折叠为 `(False, 0)`，API 只能返回笼统失败。

## Goals / Non-Goals

**Goals:**

- 让预览和实际分割共享同一章节边界解析结果。
- 对 raw regex 做保守校验，阻止明显高风险或预检失败的模式进入全文扫描。
- 让分割失败保留结构化原因，前端和 API 返回可操作错误。
- 保持现有成功路径、公开 API URL 和前端主要工作流不变。

**Non-Goals:**

- 不处理 `chapter_patterns.json` 损坏备份或配置恢复 warning。
- 不引入新的正则引擎、后台 worker 池或新第三方依赖。
- 不重做章节标题命名策略、summary batch 语义或雷点扫描迁移流程。
- 不支持远程多用户安全模型；本项目仍按本地单用户应用边界处理。

## Decisions

### 1. 引入章节边界结果模型

新增 focused 模块承载章节边界解析，例如 `logic/chapter_boundaries.py`。模型保持轻量，至少包含：

- `index`
- `title`
- `start`
- `end`
- `line_number`
- `word_count`
- `matched`，仅标题列表模式需要暴露未匹配标题

预览直接把边界结果序列化为 `ChapterPreviewItem`。实际写文件使用同一组 `start/end/title` 生成章节内容，再复用现有命名逻辑或等价 helper 写入文件。

备选方案是只让预览复用 `process_chapters_with_regex` 的 match 扫描部分。这个改动更小，但会继续保留标题列表模式的重复逻辑，也不利于把错误原因结构化，所以不选。

### 2. 保守处理 raw regex

raw regex 的目标仍是允许高级用户输入完整正则，但在用于预览或实际分割前统一执行校验：

- 空字符串、超出长度限制、编译失败直接拒绝。
- 明显高风险结构直接拒绝，例如嵌套重复量词一类模式。
- 在小样本文本上执行预检；预检失败或超过限制时拒绝。
- raw regex 不含捕获组时继续沿用自动包裹行为，保证标题 group 兼容。

备选方案是只在 UI 展示风险提示后继续执行。该方案对用户更宽松，但无法解决本地后端被高风险正则卡住的问题；本 change 以稳定性优先，因此采用保守阻止。

### 3. 用异常承载结构化失败

新增领域异常，例如 `ChapterSplitError(code, message, hint=None)`。底层解析、校验和写入失败抛出该异常；API 层转换为 HTTP 400 的 `detail`，task runner 转换为 failed 任务结果和日志。

为兼容现有调用，`split_novel_into_chapter_files` 可在过渡期继续返回 `(success, count)`，但内部不再吞掉结构化错误。直接 API、项目入库路径和任务 runner 都应尽量使用可读错误信息，而不是统一替换成“分割失败，未能生成章节文件”。

### 4. 避免失败污染项目或输出

实际分割先完成边界解析和安全校验，再创建或清空目标目录。小说总结页 `split_and_ingest_source_file` 在解析失败时不得清空现有 `inputs` 或更新 `uploads`。如果写文件阶段失败，优先写入临时目录，成功后再替换项目 `inputs`。

备选方案是在现有 `inputs` 目录内边写边失败后清理。这更容易实现，但失败期间可能破坏用户已有章节列表，不符合本轮稳定性目标。

## Risks / Trade-offs

- 高级 raw regex 被保守规则误拦截 → 错误信息必须说明原因，并建议改写为简单模式或降低正则复杂度。
- 共享边界模型会触碰多条路径 → 先补解析层 focused tests，再改 API/项目入库/前端展示，保持小步验证。
- 写入临时目录增加一次文件移动成本 → 章节文件主要是本地文本，稳定性收益高于少量 I/O 成本。
- 继续保持 `(success, count)` 兼容会让 API 过渡期略复杂 → 只在公开入口保留兼容，内部新逻辑使用结构化异常。

## Migration Plan

1. 新增共享边界解析模块和定向测试，不改变公开 API。
2. 将预览 API 改为使用共享边界结果。
3. 将实际分割和小说总结页入库改为先解析边界，再写入文件。
4. 接入 raw regex 保护和结构化错误展示。
5. 运行章节分割、项目工作区、后端 API、前端分割相关测试，以及 `openspec validate --all`。

## Open Questions

无。当前按保守 raw regex 策略推进；配置损坏备份明确不纳入本 change。
