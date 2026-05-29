# 项目稳定性与可维护性审计总览

本文是稳定性审计文档的第二轮刷新，更新日期为 2026-05-29。审计目标仍然是覆盖项目主要模块，记录已完成治理、当前剩余风险、潜在坑、可维护性问题、验证结果和后续建议修复顺序。

当前跟进状态已单独整理到 [follow-up-backlog.md](follow-up-backlog.md)：其中明确区分已实现内容、第二轮新增观察和仍未实现的后续候选事项。

## 覆盖范围

| 模块 | 报告 |
| --- | --- |
| 前端工作台 | [frontend.md](frontend.md) |
| WebUI 后端 API 与服务层 | [webui-backend.md](webui-backend.md) |
| 核心总结工作流 | [summary-workflows.md](summary-workflows.md) |
| 雷点扫描工作流 | [trigger-scan.md](trigger-scan.md) |
| 章节分割与模式配置 | [chapter-splitting.md](chapter-splitting.md) |
| 配置、文件上传与工作区 | [config-files-workspace.md](config-files-workspace.md) |
| 测试与质量保障 | [tests-and-quality.md](tests-and-quality.md) |
| OpenSpec 与文档 | [openspec-and-docs.md](openspec-and-docs.md) |
| 跨模块风险汇总 | [cross-module-risks.md](cross-module-risks.md) |
| 跟进状态与 Backlog | [follow-up-backlog.md](follow-up-backlog.md) |

## 验证基线

- `python -m pytest`：293 passed in 8.80s。
- `npm run test`（`frontend/`）：18 test files / 54 tests passed。
- `npm run build`：TypeScript 检查和 Vite 生产构建通过。
- `openspec validate --all`：21 passed。
- 前端测试输出存在 Vite/plugin 层面的 deprecation warning：`vite:react-babel` 的 `esbuild` 选项提示迁移到 `oxc` / `rolldownOptions`。当前不影响测试和构建，但属于依赖升级前需要留意的维护噪音。

## 当前跟进状态

### 已实现

- 长任务取消统一为 `cancelled`，并补齐任务终态事件和前端 SSE 断开后的状态兜底刷新。
- 雷点扫描暂停阻塞、续扫进度、历史 finding 验证、`partial_failed` 和 `unverified` warning 已完成治理。
- 聚合提示词契约已明确为当前使用 deterministic aggregation，后续 LLM 聚合保留为独立计划。
- 项目输出目录 ownership 删除保护、API 失败诊断脱敏与清理/保留策略已落地。
- 前端已区分展示 `cancelled`、`partial_failed` 和报告 warning，并对上述行为补了定向验证。
- `webui_backend/api_app.py` 已完成按职责拆分路由，公开 API URL 契约保持不变，并增加 route parity 测试。
- `webui_backend/project_workspace.py` 已保留为公开门面，项目工作区内部职责已拆入 `webui_backend/workspace_services/`。
- `frontend/src/views/TriggerScanPage.tsx` 已拆出 `frontend/src/views/trigger-scan/` 下的 profile、scan config、results、context modal 和纯 helper 模块；主页面现在主要承担状态、effects、API handlers 和 tab 组合。
- `logic/utils.py` 已缩减为兼容门面，summary output、file IO、prompt runtime、progress events、text extraction、chapter naming、batching、API logging 和 chapter writing 等职责已拆入 focused modules。
- 前端已建立最小 Vitest + Testing Library 测试基础，并覆盖雷点扫描 display/filter/profile/config/results/context 等拆分边界。
- `trigger-scan-page-modularity` 已同步为主 OpenSpec 规格，`split-trigger-scan-page` 已归档。
- Windows 输出目录打开体验已优化为显式启动 Explorer 前台窗口。
- 文章总结和自定义总结已支持部分输入失败时保留可用结果并以 `partial_failed` 暴露，任务记录和前端会展示 warning、失败 section/source file 详情和保留结果。
- 前端 API client 非 JSON 错误处理、100 MB 上传大小预检和小说页分割任务统一 `apiClient` 调用已完成，并补充 focused Vitest 覆盖。
- 章节分割已抽出共享章节边界解析，预览和实际写文件共用边界结果；raw regex 增加保守校验和预检，分割失败会暴露结构化错误原因，小说总结源文件分割失败不会清空既有章节列表。
- 任务运行时已持久化轻量终态摘要，后端重启后可查询已落盘的终态任务；重启前未结束的任务会恢复为 `interrupted`，项目历史和前端会展示中断提示，且不会阻塞新任务。
- 任务事件流已支持有界事件日志、递增 `event_id`、`Last-Event-ID`/查询游标回放、SSE heartbeat 和前端去重重连；事件日志默认位于运行时 `workspace/task_events/`，每任务最多保留 1000 条 replay 事件，事件日志文件默认保留 7 天。
- 项目历史、详情和导入路径已接入状态/输出 reconcile：任务历史终态与项目当前产物状态分开展示，异常完成项目会显示 warning、输出检查和后端生成的 repair plan；用户确认后可启动独立 `project_repair` 任务校正 metadata 或补跑小说总结缺失阶段。
- 本地配置与路径边界已完成硬化：损坏 API 配置、用户设置和章节模式配置会先备份 `.bak` 再恢复默认值并返回局部 warning；项目级自定义输出目录主动操作使用 strict 验证，历史读取使用 compat fallback warning；`open_directory` 仅允许打开当前项目有效输出目录，本地 picker/open 失败会在触发控件附近展示。
- 维护者文档首轮已完成：README 已补维护者指南，`docs/runtime_behavior_notes.md` 记录运行时规则，`docs/spec_to_test_mapping.md` 建立高价值规格到测试的映射，`docs/archived_changes_index.md` 提供归档 change 索引。

### 第二轮新增观察

- `webui_backend/workflow_services.py` 约 925 行，已经成为新的复杂编排集中点，尤其是雷点扫描 runner 内部仍包含批次调度、进度阶段、续扫、验证、失败报告和日志诊断。
- `webui_backend/project_workspace.py` 虽然已拆出 `workspace_services/`，但公开门面仍约 824 行，继续承载 metadata 模型、导入、分割入库、repair、输出选择和兼容入口。
- `TriggerScanPage.tsx` 已拆出主要 UI/纯 helper，但主页面仍约 1011 行，承担 profile/scan/result 多个状态域和大量 effect/API handler；后续新增状态时应优先抽 hook，而不是继续加在主页面。
- 雷点扫描新任务会写 `partial_failed`，但 `TriggerScanReportStore` 为兼容旧报告仍会把 `failed + findings` 读取/索引成 `completed`。这有助于旧数据可读，但会弱化旧报告的失败语义。
- `ApiConfig.max_retries` 在通用 LLM 调用中表示“总尝试次数”，而雷点扫描解析重试又用同一字段做“解析失败后的额外重试”语义，最坏情况下会放大请求次数和费用预期。
- raw regex 已有保守预检，但仍没有真正的正则执行超时；预检样本之外的极端内容仍可能触发慢匹配。
- 前端任务订阅的 `latestEventIds` / `processedEventIds` 是模块级 map，终态关闭订阅后没有清理。单次本地使用影响很小，长时间大量任务会有轻微内存增长。

### 未实现 / 仍需跟进

- 非小说工作流的深度 repair 扩展。
- 关键页面流和更系统化的前端测试覆盖。
- 打包态本地能力冒烟验证。
- 后续 LLM 聚合方案。
- 重试语义和 LLM/解析重试成本披露。
- 旧版雷点扫描报告状态迁移或兼容标记。
- 任务事件订阅生命周期清理和真实浏览器长任务交互验证。

## 顶层结论

1. 首轮审计的大部分高风险项已经关闭，当前测试基线比上一版更强：后端 293 个用例、前端 54 个用例、OpenSpec 21 个规格均通过。
2. `api_app.py` 和 `logic/utils.py` 的集中风险显著下降；新的主要维护风险转向 `workflow_services.py`、`project_workspace.py` 公开门面和 `TriggerScanPage.tsx` 编排层。
3. 任务终态、事件回放、SSE heartbeat、`interrupted`、`partial_failed`、项目 reconcile、配置恢复和路径边界已经形成较清晰的运行时 contract。后续改动应先读 [runtime_behavior_notes.md](../runtime_behavior_notes.md)，避免重新引入旧问题。
4. 雷点扫描主流程已经稳定很多，但仍需要处理旧报告状态兼容、解析重试/LLM 调用成本语义，以及真实浏览器长任务交互测试。
5. 总结工作流 partial result 语义已覆盖文章和自定义总结；小说 repair 已有首轮闭环。剩余 repair 风险主要是非小说工作流深度修复是否值得做，以及做之前如何界定安全输入、覆盖和 LLM 成本。
6. 本地单用户路径边界已经落地，frozen 打包态仍未验证；这不是日常开发阻塞项，但发布前应补人工冒烟记录。

## 建议修复顺序

| 顺序 | 风险 | 复杂度 | 建议后续动作 |
| --- | --- | --- | --- |
| 1 | `workflow_services.py` 成为新的复杂集中点 | M | 先抽雷点扫描 runner 的批次执行、验证、报告失败处理和重试策略为 focused helpers，并保持现有 workflow tests |
| 2 | 雷点扫描旧报告 `failed + findings` 被兼容显示为 `completed` | S | 增加 legacy/migrated 标记或把旧报告统一迁移为 `partial_failed`，避免历史失败语义被弱化 |
| 3 | LLM `max_retries` 与雷点解析重试语义不一致 | M | 明确 `max_attempts`、`parse_retries` 和 UI 文案，避免请求次数和费用预期漂移 |
| 4 | 前端真实交互覆盖不足，任务订阅 map 无生命周期清理 | M | 补真实浏览器长任务流验证，并在终态或历史裁剪时清理 event cursor/seen maps |
| 5 | `project_workspace.py` 门面仍偏大 | M | 继续把导入、分割入库、repair action orchestration 拆入 workspace services，保留 facade 兼容导出 |
| 6 | raw regex 仍无执行超时 | M | 如继续支持 raw regex 高级能力，评估第三方 regex timeout 或进程级隔离；当前保守预检继续保留 |
| 7 | 打包态本地能力仍未人工冒烟 | S | 补 `run_gui.py`、本地文件选择器、打开输出目录和静态资源托管的 frozen 环境冒烟记录 |
| 8 | 后续 LLM 聚合方案未设计 | M | 单独设计 API 成本、JSON 解析、fallback 行为和 UI 披露 |
| 9 | 非小说工作流深度 repair 未覆盖 | M | 仅在具体 workflow 的安全输入、覆盖和成本语义明确后，逐一扩展 repair action |

## 已知验证限制

- 未调用真实 LLM API，LLM 行为风险基于代码路径、测试替身和失败处理逻辑判断。
- 未启动浏览器做完整手工交互；前端已执行 Vitest、TypeScript 检查和生产构建。
- 未在打包后的 frozen 环境中验证 `run_gui.py`、本地文件选择器和静态资源托管。
- 未做真实超大文件、超长任务或异常网络环境压测；任务事件日志、上传预检和 raw regex 保护均基于自动化测试与代码审查判断。
