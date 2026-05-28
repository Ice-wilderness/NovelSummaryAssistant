# 项目稳定性与可维护性审计总览

本文是 `audit-project-stability-maintainability` 变更的总览报告。审计目标是覆盖项目主要模块，记录稳定性风险、潜在坑、可维护性问题、优化空间、验证结果和后续建议修复顺序。

当前跟进状态已单独整理到 [follow-up-backlog.md](follow-up-backlog.md)：其中明确区分已实现内容和仍未实现的后续候选事项。

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

- `python -m pytest`：287 passed。
- `npm run test`（`frontend/`）：51 passed。
- `npm run build`：TypeScript 检查和 Vite 生产构建通过。
- `openspec validate --all`：21 passed。

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
- 项目历史、详情和导入路径已接入状态/输出 reconcile：任务历史终态与项目当前产物状态分开展示，异常完成项目会显示 warning、输出检查和后端生成的 repair plan；用户确认后可启动独立 `project_repair` 任务校正 metadata 或补跑小说总结缺失阶段。
- 本地配置与路径边界已完成硬化：损坏 API 配置、用户设置和章节模式配置会先备份 `.bak` 再恢复默认值并返回局部 warning；项目级自定义输出目录主动操作使用 strict 验证，历史读取使用 compat fallback warning；`open_directory` 仅允许打开当前项目有效输出目录，本地 picker/open 失败会在触发控件附近展示。

### 未实现

- 完整任务事件日志、`Last-Event-ID` 回放和 SSE heartbeat。
- 非小说工作流的深度 repair 扩展。
- 前端任务订阅兜底、关键页面流和更系统化的前端测试覆盖。
- 维护者文档、运行时规则文档、OpenSpec 到测试的映射、打包态本地能力冒烟验证和 archived changes 索引。
- 后续 LLM 聚合方案。

## 顶层结论

1. 原始审计报告保留发现时的风险描述；判断当前是否仍需处理时，以本文“当前跟进状态”和 [follow-up-backlog.md](follow-up-backlog.md) 为准。
2. `webui_backend/api_app.py` 的路由集中问题、`webui_backend/project_workspace.py` 的内部职责拆分、`frontend/src/views/TriggerScanPage.tsx` 的页面职责拆分、`logic/utils.py` 的低层工具拆分、前端上传/API 健壮性、总结 partial result 语义、章节分割边界一致性、任务终态摘要持久化、项目状态/输出 reconcile 和本地配置/路径边界硬化均已完成；当前最大维护风险转向完整任务事件回放、非小说工作流深度 repair 扩展和系统化前端交互测试。
3. 任务终态和雷点扫描关键状态已经完成第一轮治理；轻量任务摘要持久化和 `interrupted` 重启提示已落地，但完整事件日志、`Last-Event-ID` 回放和 SSE heartbeat 仍未覆盖。后端重启后自动恢复 running task 不再作为后续目标，非终态任务继续以 `interrupted` 提示用户重新启动或从项目进度继续。
4. 总结工作流 partial result 语义已覆盖文章总结和自定义总结；小说总结异常完成与缺失产物修复已有首轮闭环，剩余风险主要集中在非小说工作流深度 repair 扩展和重试次数语义澄清。
5. 文件与路径能力已有 ownership 删除保护、Windows 打开目录体验优化和本地单用户边界硬化；自定义路径无效、配置损坏和本地能力不可用提示已有自动化覆盖，frozen 打包态仍建议做人工冒烟验证。

## 建议修复顺序

| 顺序 | 风险 | 复杂度 | 建议后续动作 |
| --- | --- | --- | --- |
| 1 | 完整任务事件恢复仍未覆盖 | L | 在终态摘要基础上单独设计有界事件日志、SSE heartbeat、`Last-Event-ID` 回放和前端重连/状态兜底 |
| 2 | 非小说工作流深度 repair 未覆盖 | M | 在具体 workflow 的安全输入、覆盖和成本语义明确后，逐一扩展 repair action |
| 3 | 前端任务订阅与关键页面流测试不足 | M | 补 `useTaskActions` SSE 兜底、核心页面集成测试和真实浏览器长任务交互测试 |
| 4 | 维护者文档和 spec-to-test 映射不足 | S | 补 README 维护者章节、运行时规则文档、打包态本地能力冒烟记录和 archived changes 索引 |
| 5 | 后续 LLM 聚合方案未设计 | M | 单独设计 API 成本、JSON 解析、fallback 行为和 UI 披露 |

## 已知验证限制

- 未调用真实 LLM API，LLM 行为风险基于代码路径、测试替身和失败处理逻辑判断。
- 未启动浏览器做完整手工交互；前端已执行 Vitest、TypeScript 检查和生产构建。
- 未在打包后的 frozen 环境中验证 `run_gui.py`、本地文件选择器和静态资源托管。
