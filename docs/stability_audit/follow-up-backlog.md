# 稳定性审计跟进状态

本文按实现状态整理稳定性审计后续事项。已实现部分来自已归档的 `2026-05-25-address-stability-audit-priorities`、已完成的 `split-api-app-routes`，以及后续小修；未实现部分可作为后续 OpenSpec change 的候选来源。

## 状态速览

| 状态 | 范围 |
| --- | --- |
| 已实现 | 长任务取消与终态事件、雷点扫描暂停/续扫/验证/部分失败状态、聚合提示词契约澄清、输出目录 ownership 与 API 诊断、前端状态/warning 展示、`api_app.py` 路由拆分、Windows 输出目录前台打开体验 |
| 未实现 | `project_workspace.py` / `TriggerScanPage.tsx` / `logic/utils.py` 继续拆分、任务运行时持久化与事件恢复、文章总结 partial success、状态文件与输出文件 reconcile、前端健壮性与测试体系、章节分割 raw regex 与预览一致性、配置损坏备份与 headless/frozen 提示、维护者文档、后续 LLM 聚合方案 |

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

## 未实现 / 后续候选事项

### 1. 大模块拆分与可维护性

- `webui_backend/api_app.py` 路由拆分已完成；后续若继续优化，重点应放在共享 helper 是否下沉到服务层，而不是再次调整公开 API。
- 拆分 `webui_backend/project_workspace.py`：把 metadata、uploads、output migration、import recognition、deletion protection 等职责分层。
- 拆分 `frontend/src/views/TriggerScanPage.tsx`：拆成 profile 管理、scan config、report list/detail、finding review、context modal 等组件和 hooks。
- 拆分 `logic/utils.py`：逐步拆成 file utils、prompt runtime、chapter naming、API logging、batch allocation 等小模块。

建议：这些应作为无行为变化重构来做，每次只拆一个边界，并以现有测试和新增烟雾测试保护。

### 2. 任务运行时持久化与事件恢复

- 任务运行时仍主要驻留内存；本次只处理终态事件和前端断线兜底，不实现完整任务事件落盘。
- 后端重启后，旧 task event history、last-event-id 回放和 running task 恢复仍未覆盖。
- 项目 metadata 目前主要保存最近任务状态，未建立完整任务摘要历史。

建议：先设计 terminal task summary 持久化，再考虑 SSE heartbeat、事件回放和重启后的用户提示。

### 3. 文章总结 partial success

- 文章总结 section 级失败后继续生成终稿的语义未在本次完整治理。
- 失败 section 列表、最终结果 warning、是否允许继续生成终稿的配置/UI 决策仍需确认。
- 自定义总结是否需要类似 partial success 语义，也需要在实现前确认。

建议：单独新建 change，先定义文章总结 partial 状态和用户可见 warning，再补服务层测试。

### 4. 状态文件与输出文件 reconcile

- `StateManager` 同时依赖 JSON 状态和输出文件存在性判断完成度的问题未覆盖。
- 手工删除输出、格式切换、导入旧项目时的异常状态展示仍未统一。

建议：先定义“完成状态来源”的优先级，再为导入和项目进入时增加 reconcile 结果与 warning。

### 5. 前端健壮性与测试体系

- 前端仍缺少系统化组件测试或交互测试；本次只要求对新增状态和提示补 focused tests 或等价验证。
- `frontend/src/api/client.ts` 的非 JSON 错误响应解析仍未优化。
- `useManagedProject.uploadFiles` 和小说页上传仍会在浏览器端完整读入大文件，未处理内存占用风险。
- `NovelSummaryPage.confirmSplitAndIngest` 仍有原生 `fetch` 路径，未收敛到统一 `apiClient`。
- `PromptEditorPage` 使用 `JSON.stringify` 判断脏状态，当前可接受，但字段增多后需要规范化比较。

建议：先补最小前端测试基础，再处理 API client 和上传内存问题。

### 6. 章节分割与模式配置

- raw regex 仍缺少运行时保护，复杂正则可能造成长时间阻塞。
- `split_novel_into_chapter_files` 仍可能把结构化错误折叠成 `(False, 0)`。
- 预览和实际分割逻辑仍有重复实现，边界条件下可能不一致。
- `PatternConfigService` 配置损坏时自动重置但缺少备份和用户提示。

建议：先抽出共享章节边界解析器，再补 regex 预检/限制和结构化错误返回。

### 7. 配置、路径与本地环境边界

- 自定义输出目录无效时的静默回退未完整治理；本次只处理删除 ownership 边界。
- `/api/browse/file`、`/api/browse/directory`、`open_directory` 在 headless、无 tkinter、frozen 打包环境中的错误提示仍需加强；Windows 前台打开体验已做基础优化。
- 配置文件损坏时返回默认值但缺少 `.bak` 备份和 UI warning，包括 API configs、user settings 等。
- `open_directory` 的安全边界可进一步限制为项目/输出范围。

建议：先明确项目定位为本地单用户应用，再统一本地能力不可用时的错误文案和 API 行为。

### 8. 文档与 OpenSpec 维护

- README 仍缺少维护者视角的测试命令、常见故障、运行时生成目录说明和 OpenSpec 流程说明。
- 关键运行时规则尚未沉淀成 `docs/runtime_behavior_notes.md` 一类文档。
- 高价值 OpenSpec 条目和测试文件之间仍缺少 spec-to-test 映射。
- archived changes 数量较多，缺少索引摘要。

建议：这些可以作为文档型 change 单独完成，风险低，但能明显降低后续接手成本。

### 9. 后续 LLM 聚合方案

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

1. `project_workspace.py`、`TriggerScanPage.tsx` 和 `logic/utils.py` 的无行为拆分，为后续功能修复降低冲突。
2. 文章总结 partial success，避免用户拿到看似完整但缺 section 的结果。
3. 前端 API client 和大文件上传健壮性。
4. 章节分割 raw regex 保护和预览/实际一致性。
5. 运行时持久化和维护者文档。
