# 稳定性审计跟进状态

本文按实现状态整理稳定性审计后续事项。已实现部分来自已归档的 `2026-05-25-address-stability-audit-priorities`、`2026-05-26-split-api-app-routes`、`2026-05-26-split-project-workspace-services`、`2026-05-26-split-trigger-scan-page`，以及 `split-logic-utils`、`add-summary-partial-status`、`harden-frontend-api-upload`、`harden-chapter-splitting-boundaries`、`persist-task-terminal-summaries`、`reconcile-project-state-outputs` 和后续小修；未实现部分可作为后续 OpenSpec change 的候选来源。

## 状态速览

| 状态 | 范围 |
| --- | --- |
| 已实现 | 长任务取消与终态事件、任务终态摘要持久化和 `interrupted` 重启提示、雷点扫描暂停/续扫/验证/部分失败状态、聚合提示词契约澄清、输出目录 ownership 与 API 诊断、前端状态/warning 展示、`api_app.py` 路由拆分、`project_workspace.py` 内部职责拆分、`TriggerScanPage.tsx` 页面职责拆分、`logic/utils.py` 低层工具拆分、前端最小测试基础、前端 API/上传健壮性、Windows 输出目录前台打开体验、文章/自定义总结 partial result 状态、章节分割边界一致性与 raw regex 保护、状态文件与输出文件 reconcile、用户确认后的项目修复任务 |
| 未实现 | 完整任务事件日志、`Last-Event-ID` 回放、SSE heartbeat 和 running task 自动恢复、非小说工作流的深度 repair 扩展、前端任务订阅兜底与更系统化测试、配置损坏备份与 headless/frozen 提示、维护者文档、后续 LLM 聚合方案 |

## 已实现

### 1. 长任务取消与终态事件

- 小说总结、文章总结、自定义总结、章节分割、雷点扫描的用户取消统一传播为 `asyncio.CancelledError`。
- `TaskRuntime` 将用户接受的取消记录并发射为 `cancelled`，不再混入 `failed` 或成功完成。
- 任务事件流在 `completed`、`failed`、`cancelled`、`partial_failed` 等终态后暴露终态，前端 SSE 断开后会拉取最新任务状态兜底。
- 已补业务 runner 级取消测试和相关运行时测试。

### 2. 雷点扫描暂停、续扫、验证与状态

- 精确扫描和验证路径改为真正阻塞的异步暂停门，避免暂停后继续发起后续 API 调用。
- 续扫进度统一使用 `selected_total`、`completed_from_resume`、`pending_total`、`processed_current_run`，避免完成数回退或超过总数。
- 扫描状态和报告模型保留 finding 验证状态与来源信息，续扫时区分新增 finding 和历史 finding。
- 历史 finding 缺失上下文时标记 `unverified` warning；非取消的部分执行结果使用 `partial_failed`，用户取消不再写成 `completed`。
- 已补暂停阻塞、续扫分母、历史 finding 验证、`unverified` warning 和 `partial_failed` 状态测试。

### 3. 聚合提示词契约

- 当前雷点扫描聚合保持 deterministic aggregation，不引入额外 LLM 聚合调用。
- 提示词工作流元数据、API 和前端提示已调整，避免把 aggregation prompt 表达为会影响当前扫描结果的活跃 LLM 节点。
- 后续 LLM 聚合方案保留为独立计划，需另行设计 API 成本、JSON 解析、fallback 和 UI 披露。

### 4. 输出目录 ownership 与 API 诊断

- 后端创建的 managed export 目录写入 ownership metadata。
- 删除项目时仅删除 ownership 与当前项目匹配的输出目录；自定义、导入、缺失 metadata 或 ownership 不匹配的目录会保留，并向 WebUI 返回说明信息。
- API 失败诊断继续保留完整非密钥输入/输出，同时脱敏 API key、Authorization 等敏感凭据。
- 已增加失败诊断日志清理/保留路径和对应测试。

### 5. 前端状态与 warning 展示

- 前端区分展示 `cancelled`、`partial_failed` 和保留的部分结果，不再笼统显示为普通失败。
- 雷点扫描报告会展示 `unverified`、缺失上下文和部分结果保留等 warning。
- 终态事件和 SSE 兜底拉取后会刷新项目历史与当前项目状态。

### 6. 验证

- 已运行任务运行时、工作流服务、雷点扫描 pipeline/reporting、项目工作区和 LLM 诊断等定向测试。
- 已运行 `python -m pytest`。
- 已运行 `npm run build`。

### 7. 后端 API 路由拆分

- `webui_backend/api_app.py` 已保留为应用组装入口，负责 app state、共享 route context、路由注册和静态前端 fallback。
- API 路由已按 config/prompts/settings、trigger profile/pattern、project/upload/path、trigger scan、summary/splitter/task runtime 拆入 `webui_backend/routes/`。
- 已增加 route table parity 测试，防止公开 API method/path 漏注册。
- 拆分过程中保持现有 URL、请求/响应结构、错误状态码和前端调用路径不变。
- 已按功能块提交并运行对应定向测试、完整 `python -m pytest` 和 `npm run build`。

### 8. 本地输出目录打开体验

- Windows 下打开输出目录改为显式启动 `explorer.exe` 并请求普通显示窗口，减少目录在后台静默打开、需要从任务栏手动切换的情况。
- macOS 和 Linux 仍使用原有 `open` / `xdg-open` 路径。
- 已补 Windows 分支调用测试。

### 9. 项目工作区服务拆分

- `webui_backend/project_workspace.py` 已保留为公开兼容门面，现有 `ProjectWorkspaceService`、metadata 模型和 helper 导入路径继续可用。
- 项目工作区内部职责已拆入 `webui_backend/workspace_services/`，覆盖 uploads、outputs、progress、low-state utilities 和 local open 等边界。
- 拆分保持现有 WebUI API、工作区文件布局、输出目录 ownership、导入识别、删除保护和目录打开行为不变。
- 已运行项目工作区、API、import facade 和完整 Python 测试；前端构建未受该拆分影响。

### 10. 雷点扫描页面拆分与前端测试基础

- `frontend/src/views/TriggerScanPage.tsx` 已从约 90 KB 的集中页面拆为受控页面编排和 `frontend/src/views/trigger-scan/` 下的领域模块。
- 当前模块边界包括 `ProfileTab.tsx`、`ScanConfigTab.tsx`、`ResultsTab.tsx`、`ContextModal.tsx`、`display.ts`、`profileDraft.ts`、`resultFilters.ts` 和 `options.ts`。
- 主页面保留跨 tab 状态、effects、API handlers、任务事件 wiring 和 tab 组合；profile 管理、扫描配置、结果筛选/分页/复核、上下文展示已经下沉到 focused modules。
- 已新增 Vitest + Testing Library 测试基础，`npm run test` 覆盖 display、profile draft、result filters、ProfileTab、ScanConfigTab、ResultsTab 和 ContextModal。
- 已新增主规格 `openspec/specs/trigger-scan-page-modularity/spec.md`，归档 change 为 `openspec/changes/archive/2026-05-26-split-trigger-scan-page/`。

### 11. 低层工具模块拆分

- `logic/utils.py` 已缩减为兼容门面，继续支持既有 `from logic.utils import ...`、`from logic import utils` 和相关测试 patch 路径。
- 低层职责已拆入 `logic/summary_outputs.py`、`logic/file_io.py`、`logic/prompt_runtime.py`、`logic/progress_events.py`、`logic/text_extraction.py`、`logic/chapter_naming.py`、`logic/batching.py`、`logic/api_logging.py` 和 `logic/chapter_writing.py`。
- 拆分保持 summary output 路径、提示词加载、API 诊断日志、章节命名/排序、批次分配和章节写入行为不变。
- 已运行 focused tests 和完整 `python -m pytest`；前端未触及。

### 12. 文章/自定义总结 partial result 状态

- `TaskRuntime` 已支持结构化 `TaskRunOutcome` 和 summary 类任务的 `partial_failed` 终态，旧字符串 runner 行为保持兼容。
- 文章总结 section 级失败后，如果至少有可用 section summary 且最终总结成功生成，会保留最终总结并以 `partial_failed` 暴露 warning、失败 section 列表和最终输出路径；全部 section 失败或最终总结失败仍为 `failed`。
- 自定义总结素材读取部分失败后，如果至少有可用素材且最终 LLM 输出成功，会保留生成文本并以 `partial_failed` 暴露 warning 和失败 source file 列表；全部素材失败或最终 LLM 调用失败仍为 `failed`。
- API task response 和项目历史会保留 `partial_failed`、warnings 与失败单元结构化详情，前端文章/自定义页面会显示“部分结果”提示、失败输入和保留结果。
- 已运行 `tests/test_task_runtime.py`、`tests/test_article_summary_logic.py`、`tests/test_custom_summary_logic.py`、相关 workflow/API 定向测试、`npm run test -- SummaryPartialNotice.test.tsx`、完整 `python -m pytest`、`npm run test`、`npm run build` 和 `openspec validate --all`。

### 13. 前端 API client 与上传健壮性

- `frontend/src/api/client.ts` 已对非 JSON 错误响应保留 HTTP status，并通过 `ApiError` 暴露 status text 或短文本预览，不再把 HTML/纯文本错误页显示成裸 `SyntaxError`。
- 前端新增 100 MB 单文件上传预检，`useManagedProject.uploadFiles` 和 `NovelSummaryPage.handleSourceUpload` 会在 `arrayBuffer()` 前拒绝超限 TXT，避免浏览器先完整读入大文件。
- `NovelSummaryPage.confirmSplitAndIngest` 已收敛到 `apiClient.startSplitter`，不再在页面内手写 `/api/tasks/splitter` 的 `fetch` 和错误解析。
- 已新增 `frontend/src/api/client.test.ts`、`frontend/src/hooks/useManagedProject.test.tsx` 和 `frontend/src/views/NovelSummaryPage.test.tsx`，覆盖非 JSON 错误、上传大小预检和分割任务 API client 调用。
- 已运行 focused frontend tests、完整 `npm run test`、`npm run build` 和 `openspec validate harden-frontend-api-upload --strict`。

### 14. 章节分割边界一致性与 raw regex 保护

- 已新增 `logic/chapter_boundaries.py`，集中承载章节边界结果、结构化 `ChapterSplitError`、默认/正则/标题列表边界解析，以及 raw regex 校验和预检。
- 预览 API、默认/正则/标题列表实际分割现在共用章节边界结果，避免预览数量、标题顺序和实际写出的单章文件漂移。
- raw regex 在进入全文扫描前会拒绝空值、语法错误、过长表达式、明显高风险嵌套重复和预检异常，并返回用户可读错误。
- direct split、splitter task 和小说总结源文件分割会保留明确失败原因，不再只暴露笼统 `(False, 0)` 或“未能生成章节文件”。
- 小说总结页源文件分割先写入临时目录，成功后才替换项目 `inputs/uploads`；失败时保留既有章节列表。
- 前端分割页和小说总结页会显示“分割失败”原因，并补充失败时不清空源文件/章节状态的 focused Vitest 覆盖。
- 已运行 `tests/test_chapter_boundaries.py`、章节粒度、项目工作区、workflow/API focused tests、完整 `python -m pytest`、完整 `npm run test`、`npm run build`、`openspec validate harden-chapter-splitting-boundaries --strict` 和 `openspec validate --all`。

### 15. 任务终态摘要持久化与中断状态

- `TaskRuntime` 已支持轻量任务摘要持久化，默认写入 `runtime_base/workspace/task_summaries/`。
- 任务创建、生命周期关键状态变化和 `success`、`failed`、`cancelled`、`partial_failed` 等终态会更新摘要；后端重启后 `/api/tasks/{task_id}` 和 `/api/tasks` 可读取已落盘任务。
- 后端重启前仍处于 `pending`、`running`、`paused` 或 `canceling` 的任务会恢复为 `interrupted`，并保留用户可见 warning/error，说明任务无法自动续跑。
- `/api/tasks/{task_id}/events` 对已落盘终态或 `interrupted` 任务会暴露最终状态并关闭，不承诺完整历史事件回放。
- 项目历史会优先使用已加载的任务摘要状态；缺失或不可读摘要时保留既有项目进度 fallback。
- 前端共享任务状态、历史项目状态和雷点扫描状态 helper 已支持 `interrupted`，并避免把中断状态误显示为失败、成功、取消或部分结果。
- 已运行 `tests/test_task_runtime.py`、`tests/test_api_app.py`、前端 focused tests、完整 `python -m pytest`、完整 `npm run test`、`npm run build`、`openspec validate persist-task-terminal-summaries --strict` 和 `openspec validate --all`。

### 16. 项目状态/输出 Reconcile 与用户触发修复

- 后端已新增项目级 `reconciliation_status`、`reconciliation_warnings`、`output_checks` 和 `repair_plan`，在项目历史、详情和导入路径统一检查 metadata、任务摘要、低层状态文件、中间产物和最终输出文件。
- 任务 lifecycle 与项目 reconcile 状态已分离：`success`、`partial_failed` 等仍表示历史任务终态；`abnormal_completed` 表示曾有完成/部分完成记录，但当前关键输出缺失、不可读或格式不一致；`incomplete` 表示没有可靠完成记录且没有完成产物；`state_incomplete` 表示有产物但状态 metadata 不足。
- Repair plan 由后端生成，前端只提交 action id。仅 metadata、进度摘要、历史索引、路径绑定或导入缓存位置校正属于无 LLM 修复；任何小总结、大总结、超级总结、终极总结、文章总结或自定义总结正文补齐都按可能调用 LLM 处理，并要求用户确认费用、内容变化和覆盖风险。
- 项目修复以新的 `project_repair` 任务运行，复用现有任务状态查询和事件订阅，不把异常完成项目静默当成普通未完成任务自动续跑。
- 首轮深度修复聚焦小说总结；其他 workflow 若没有明确安全修复实现，会返回 `unsupported` 或 blocked repair action，提示用户手动检查或重新运行。
- WebUI 历史项目会同时保留历史任务状态并标出“异常完成”，项目详情会显示缺失/不一致 warning、输出检查和可执行/blocked 修复动作。
- 已运行 focused 后端/前端测试、完整 `python -m pytest`、完整 `npm run test`、`npm run build` 和 `openspec validate --all`。

## 未实现 / 后续候选事项

### 1. 完整任务事件恢复与运行中任务恢复

- 当前已实现轻量任务摘要持久化、终态查询和 `interrupted` 重启提示。
- 完整 task event history、`Last-Event-ID` 回放和 SSE heartbeat 仍未覆盖。
- 后端重启后自动恢复正在执行的 running task 仍未覆盖；现阶段明确要求用户重新启动或从项目进度继续。

建议：如确实需要更强恢复能力，再单独设计事件日志、heartbeat、回放协议和 running task 恢复边界，避免和当前轻量摘要机制混在一起。

### 2. 非小说工作流的深度 Repair 扩展

- 首轮状态/输出 reconcile 与 repair plan 已统一接入项目模型和 WebUI。
- 小说总结已覆盖异常完成识别、metadata 校正、用户确认后的缺失总结阶段补跑和 blocked repair 提示。
- 文章总结、自定义总结、章节分割和雷点扫描目前只保留统一状态模型、有限 reconcile 或 unsupported/blocked repair plan，尚未逐一实现同等深度的自动修复。

建议：后续只在具体 workflow 的安全输入、输出覆盖和 LLM 成本语义明确后，再为该 workflow 单独扩展 repair action。

### 3. 前端任务订阅与测试体系

- 前端已有最小 Vitest + Testing Library 基础，雷点扫描拆分边界、summary partial warning、API client 错误解析、上传大小预检和小说页分割任务路径已有 focused tests。
- `useTaskActions` 的 SSE 错误兜底和更完整的 running task 低频轮询策略仍可继续补强。
- 关键页面流仍缺少更系统化的集成测试或真实浏览器交互测试。
- `PromptEditorPage` 使用 `JSON.stringify` 判断脏状态，当前可接受，但字段增多后需要规范化比较。

建议：沿用现有 Vitest 基础，优先补 `useTaskActions` SSE 兜底、核心页面流和真实浏览器长任务交互测试。

### 4. 配置、路径与本地环境边界

- 自定义输出目录无效时的静默回退未完整治理；本次只处理删除 ownership 边界。
- `/api/browse/file`、`/api/browse/directory`、`open_directory` 在 headless、无 tkinter、frozen 打包环境中的错误提示仍需加强；Windows 前台打开体验已做基础优化。
- 配置文件损坏时返回默认值但缺少 `.bak` 备份和 UI warning，包括 API configs、user settings、chapter patterns 等。
- `open_directory` 的安全边界可进一步限制为项目/输出范围。

建议：先明确项目定位为本地单用户应用，再统一本地能力不可用时的错误文案和 API 行为。

### 5. 文档与 OpenSpec 维护

- README 仍缺少维护者视角的测试命令、常见故障、运行时生成目录说明和 OpenSpec 流程说明。
- 关键运行时规则尚未沉淀成 `docs/runtime_behavior_notes.md` 一类文档。
- 高价值 OpenSpec 条目和测试文件之间仍缺少 spec-to-test 映射。
- archived changes 数量较多，缺少索引摘要。

建议：这些可以作为文档型 change 单独完成，风险低，但能明显降低后续接手成本。

### 6. 后续 LLM 聚合方案

- 本次不引入 LLM aggregation prompt 调用。
- 建议后续单独新建 OpenSpec change：`add-llm-trigger-aggregation`。
- 后续如果要做，需要明确以下设计点：
  - API 成本：是否每次扫描额外调用聚合模型、是否允许用户关闭、如何在 UI 上提示额外 token/费用。
  - JSON 解析：aggregation prompt 输出的 `ScanEvent` schema、事件与 finding id 的引用校验、解析失败的错误诊断文件。
  - 失败 fallback：聚合 LLM 调用失败、输出为空、JSON 不合法或引用不存在 finding 时，是否退回 deterministic aggregation。
  - deterministic fallback：保留当前本地聚合作为兜底路径，并在报告 metadata 中标记事件来源。
  - UI 披露：提示词编辑器、扫描配置和报告详情需要明确“LLM 聚合已启用/未启用”、失败 fallback 后采用的聚合来源。
  - 测试矩阵：成功解析、引用缺失、JSON 解析失败、API 失败、fallback 报告状态和 UI 展示都需要定向测试。

建议：在雷点扫描稳定后再单独做，避免和本次稳定性修复混在一起。

## 下次优先级建议

1. 配置损坏备份、headless/frozen 提示和本地路径边界。
2. 完整任务事件日志、SSE heartbeat、`Last-Event-ID` 回放和 running task 恢复方案。
3. 非小说工作流的深度 repair 扩展。
4. 前端任务订阅兜底和核心页面流测试。
5. 维护者文档和 archived changes 索引。
