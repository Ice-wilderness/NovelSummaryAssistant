## Why

当前项目已经具备章节拆分、小说总结、提示词编辑和 WebUI 任务运行能力，但用户无法在阅读前按自己的敏感剧情规则进行系统化避雷。雷点扫描需要稳定的章节/段落定位、可配置规则档案、可复核结果和低剧透展示，因此需要在现有小说总结项目体系上新增一条可续扫、可导出的扫描工作流。

## What Changes

- 新增“雷点扫描 / 阅读避雷扫描”一级入口，并在页面内提供档案管理、扫描配置、扫描结果三个 Tab。
- 新增全局雷点档案与规则管理，支持规则分组、内置模板规则、正例/反例、匹配策略、严重度阈值和启用状态。
- 新增双模式扫描：
  - 混合模式：小总结粗筛 → 原文精扫 → 可选二次验证 → AI 聚合去重。
  - 精确模式：直接按章节原文精扫 → 可选二次验证 → AI 聚合去重。
- 新增段落切分与缓存，给每章稳定分配 `P001` 等段落编号，并要求模型返回精确段落位置。
- 新增 ScanFinding、ScanEvent、ScanReport、跳读清单等数据结构，扫描结果保存到项目输出目录 `trigger_scan/` 下。
- 新增三档剧透描述，扫描时同时生成简略、标准、详细内容，UI 通过全局和单条滑块切换显示。
- 新增结果复核、误报标记、用户备注、上下文查看、事件视图/逐条视图、筛选、历史扫描记录和 MD/JSON 导出。
- 新增章节级断点续扫，扫描状态保存到 `.summarizer_cache/scan_state_{task_id}.json`，中断后从未完成章节继续。
- 新增仅小总结任务模式，使混合扫描可在缺少小总结时只补齐小总结而不继续推进到大总结。
- 新增小说总结工作流输出格式选择，支持 Markdown 与纯文本，默认输出 Markdown，并要求后续总结、项目进度和扫描读取逻辑兼容 `.md` 与 `.txt`。
- 新增扫描阶段输入批次配置：粗筛默认每批读取 3 个小总结，精确扫描默认每批读取 5 章，二次验证默认每批读取 5 章。
- 新增四套可编辑提示词：`trigger_coarse_scan`、`trigger_precise_scan`、`trigger_verification`、`trigger_aggregation`。
- **BREAKING**：章节拆分移除 `chapters_per_file`，拆分输出固定为一章一个文件；总结阶段新增 `summary_batch_size` 控制小总结合并章节数，新项目默认值为 10。
- **BREAKING**：旧的多章合并项目在用于新扫描/总结流程前需要检测并迁移为单章文件，同时把旧 `chapters_per_file` 迁移为项目的 `summary_batch_size`。

## Capabilities

### New Capabilities

- `chapter-processing-granularity`: 章节拆分固定单章文件、总结批量粒度解耦、旧项目多章合并检测与迁移。
- `trigger-profile-management`: 全局雷点档案、规则分组、内置模板规则、规则 CRUD 与规则变更提示。
- `trigger-scan-workflow`: 混合/精确扫描、段落预处理、粗筛、精扫、二次验证、聚合去重、断点续扫和实时进度。
- `trigger-scan-results`: 扫描报告、事件/逐条结果视图、三档剧透、上下文查看、复核、跳读清单、历史记录和导出。

### Modified Capabilities

- `webui-workbench`: 增加雷点扫描一级导航入口，并使现有小说总结/章节拆分页面展示新的总结批量配置和单章拆分语义。
- `task-runtime-api`: 增加雷点扫描任务类型、仅小总结任务模式、章节级扫描进度事件和中断恢复状态。
- `managed-project-outputs`: 将扫描报告、历史记录、跳读清单和导出文件纳入项目输出目录管理，并支持旧项目迁移后的状态识别。
- `configuration-management`: 持久化雷点档案、总结输出格式、扫描默认配置、扫描 API/验证 API 选择、扫描阶段批次大小和提示词相关默认值。
- `workflow-prompt-composition`: 增加雷点粗筛、精扫、二次验证、聚合四类提示词节点和扫描变量渲染校验。

## Impact

- 后端章节拆分、总结阶段编排、任务运行器、StateManager、项目工作区服务、扫描结果存储和导出逻辑。
- WebUI 侧边栏导航、章节拆分页、小说总结页、雷点扫描页、提示词编辑器、任务日志/进度面板和项目历史恢复控件。
- 本地数据布局：`workspace/trigger_profiles/`、`exports/{slug}/trigger_scan/`、`.summarizer_cache/paragraph_index/`、`.summarizer_cache/scan_state_{task_id}.json`。
- API 配置与调用路径：扫描 API 多选、验证 API 选择、粗筛/精扫/验证/聚合阶段的结构化 JSON 解析和失败诊断。
- 测试范围：章节拆分粒度、旧项目迁移、summary_batch_size、总结输出格式、仅小总结模式、档案 CRUD、扫描前置检查、扫描批次配置、段落编号稳定性、扫描续扫、结果复核、跳读清单和导出。
- 实施约束：每完成一个功能块并通过对应检查后，提交一次 git commit，避免大批量未提交变更堆积。
