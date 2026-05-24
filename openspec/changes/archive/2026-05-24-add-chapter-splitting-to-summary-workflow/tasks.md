## 1. 正则配置模块后端

- [x] 1.1 创建 `webui_backend/pattern_config_service.py`，定义 PatternConfig 数据类（id, name, pattern, regex_mode: "raw"|"simple", description, is_preset, created_at, updated_at）和 PatternConfigService（CRUD + 导入/导出），持久化到 `chapter_patterns.json`
- [x] 1.2 在 `config_models.py` 中添加 `PatternConfig` 和 `PatternConfigListResponse` 数据类
- [x] 1.3 在 `api_app.py` 中添加正则配置 REST 端点：`GET/POST /api/patterns`、`PUT/DELETE /api/patterns/{id}`、`POST /api/patterns/import`、`GET /api/patterns/{id}/export`
- [x] 1.4 在 `api_app.py` 启动时初始化 PatternConfigService，若 `chapter_patterns.json` 不存在则自动创建默认预设配置（将 default_strategy.py 内置正则打包为名为"默认-第X章(节|回)"的预设配置，regex_mode=raw）
- [x] 1.5 在 `splitters/regex_strategy.py` 中新增 `run_with_raw_regex()` 函数，接收完整正则字符串，自动检测并包裹无捕获组的正则（包裹为 `^\s*(({regex}).*)`），编译后传给 `process_chapters_with_regex`

## 2. 分割预览后端

- [x] 2.1 在 `logic/chapter_splitter.py` 中添加 `preview_split()` 函数，接收 content/mode/pattern_config，扫描匹配返回 `[{title, line_number, start_pos}]` 列表，不写入任何文件
- [x] 2.2 在 `api_app.py` 中添加 `POST /api/chapters/preview-split` 端点，接收源文件 base64 内容 + 分割参数（mode, pattern_config, title_list, handle_volumes），返回章节预览列表
- [x] 2.3 在 `config_models.py` 中添加 `SplitPreviewRequest`、`ChapterPreviewItem`、`SplitPreviewResult` 数据类

## 3. 分割上下文分支后端

- [x] 3.1 在 `SplitterRequest` 中添加 `context` 字段（"novel_summary" | "chapter_split"）
- [x] 3.2 在 `project_workspace.py` 添加 `split_and_ingest_source_file()` 方法：对源文件执行分割，将结果章节写入项目 inputs 目录，替换 project.uploads 列表
- [x] 3.3 在 `workflow_services.py` 的分割任务运行器中，根据 context 参数选择输出目标（novel_summary→项目 inputs；chapter_split→独立导出目录）
- [x] 3.4 在 `api_app.py` 的 `/api/tasks/splitter` 端点中传递 context 参数

## 4. 前端类型与 API 层

- [x] 4.1 在 `types.ts` 中添加 `PatternConfig`、`SplitPreviewRequest`、`ChapterPreviewItem`、`SplitPreviewResult` 类型定义
- [x] 4.2 在 `client.ts` 中添加正则配置 API 方法（listPatterns, createPattern, updatePattern, deletePattern, importPatterns, exportPattern）和 `previewSplit()` 方法

## 5. 前端正则配置管理 UI

- [x] 5.1 创建 `frontend/src/components/patterns/PatternConfigManager.tsx` 配置管理浮层组件：列表展示（标注 raw/simple 模式和预设标记）、新建、编辑（名称 + 正则文本域 + 模式选择 + 描述）、删除（预设配置禁止删除）、导入 JSON 文件、导出单个配置
- [x] 5.2 创建 `frontend/src/components/patterns/PatternSelector.tsx` 配置选择器组件：下拉选择当前配置 + 正则表达式只读预览 + "编辑"按钮打开 PatternConfigManager

## 6. 前端分割预览面板

- [x] 6.1 创建 `frontend/src/components/splitting/SplitPreviewPanel.tsx` 预览面板组件：章节总数醒目展示 + 可滚动名称列表（序号 + 标题文字 + 行号）+ 确认/取消按钮 + 加载/空结果/错误状态

## 7. 小说总结页面集成

- [x] 7.1 在 [NovelSummaryPage.tsx](frontend/src/views/NovelSummaryPage.tsx) 的"项目与文件"区域新增"源文件（待分割）"卡片：单文件 TXT 上传、模式选择（默认/正则/标题列表）、正则模式下显示 PatternSelector、分卷处理开关
- [x] 7.2 源文件区域标注为"源文件（待分割）"，与下方"已分割章节"区域用分割线和标题明确区分
- [x] 7.3 添加"预览分割"按钮，调用 previewSplit API → 在 SplitPreviewPanel 中展示结果
- [x] 7.4 添加"确认分割并导入"按钮，在预览满意后触发分割任务（context=novel_summary），完成后自动刷新章节列表
- [x] 7.5 更新 `canStart` 逻辑：仅基于"已分割章节"区域的文件数判断，源文件区域不影响

## 8. 章节分割页面升级

- [x] 8.1 在 [SplitterPage.tsx](frontend/src/views/SplitterPage.tsx) 中，将"正则"模式下的 textarea 替换为 PatternSelector 组件
- [x] 8.2 在 SplitterPage 中添加"预览分割"按钮和 SplitPreviewPanel
- [x] 8.3 保持"开始"按钮现有行为（context=chapter_split，独立导出目录逻辑不变）
- [x] 8.4 标题列表模式也复用预览功能

## 9. 验证与收尾

- [x] 9.1 端到端验证：小说总结页 → 上传源文件 → 选择正则配置 → 预览 → 确认分割 → 章节列表自动更新 → 启动总结
- [x] 9.2 端到端验证：章节分割页 → 上传源文件 → 选择正则配置 → 预览 → 分割 → 导出到独立目录
- [x] 9.3 验证复杂正则：导入你提供的零宽断言正则，预览/分割不同格式的小说，确认匹配正确
- [x] 9.4 验证正则配置的创建/编辑/删除/切换/导入/导出全流程
- [x] 9.5 验证预设默认配置不可删除，且可正常使用
