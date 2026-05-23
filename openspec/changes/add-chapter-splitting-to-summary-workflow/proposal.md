## Why

当前小说总结工作流与章节分割功能相互独立，用户需要先在"章节分割"页面对源文件进行切割，再切换到"小说总结"页面手动上传分割后的章节文件。这种割裂的流程增加操作步骤，且用户无法在切割前预览结果，容易切割错误后才察觉。将章节分割集成到小说总结工作流中，并提供可配置的正则模块和预览功能，能显著降低使用门槛和出错率。

## What Changes

- 小说总结页面新增源文件上传入口，与分割后的章节列表在 UI 上明确区分，标注"源文件（待分割）"和"已分割章节"
- 章节分割的正则模式从当前的自由文本输入升级为独立的正则配置模块，每个配置存储**完整正则表达式**（支持零宽断言、多分支、Unicode 字符类等高级语法），可命名、可切换、可导入/导出。同时保留 `第n章` 占位符作为简化构建器。系统出厂预置默认配置（基于现有 default_strategy.py 的正则），用户可维护多套配置以适配不同类型小说的章节标题格式
- 导入源文件后，展示分割预览：章节总数及各章名称列表，用户确认后再执行实际分割
- 从小说总结入口执行的分割，结果直接作为项目章节文件使用，无需二次导入；从"章节分割"独立入口执行的分割，保持原有的独立导出目录逻辑不变

## Capabilities

### New Capabilities
- `chapter-splitting-integration`: 小说总结页面集成源文件上传与章节分割，分割结果直接作为项目章节
- `chapter-pattern-config`: 独立的章节分割正则配置模块，支持多配置管理、切换、导入/导出
- `split-preview`: 源文件分割前预览章节数量和名称列表

### Modified Capabilities
<!-- 无现有 spec 需要修改，项目暂无已有 spec -->

## Impact

- **前端**：[NovelSummaryPage.tsx](frontend/src/views/NovelSummaryPage.tsx) — 新增源文件上传区域、分割预览面板；[SplitterPage.tsx](frontend/src/views/SplitterPage.tsx) — 使用新的正则配置模块替换自由文本输入
- **后端**：[api_app.py](webui_backend/api_app.py) — 新增分割预览 API、正则配置 CRUD API；[project_workspace.py](webui_backend/project_workspace.py) — 新增源文件存储和分割后直接写入项目的能力
- **分割策略**：[regex_strategy.py](splitters/regex_strategy.py) — 支持从配置模块加载正则模式
- **新增**：正则配置存储模块、正则配置管理 API/UI 组件
