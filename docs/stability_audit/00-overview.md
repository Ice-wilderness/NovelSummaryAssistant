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

- `python -m pytest`：217 passed。
- `npm run test`（`frontend/`）：20 passed。
- `npm run build`：TypeScript 检查和 Vite 生产构建通过。
- `openspec validate --all`：19 passed。

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

### 未实现

- 任务运行时持久化、事件回放和后端重启后的任务恢复。
- 文章总结 partial success、状态文件与输出文件 reconcile。
- 前端 API client 非 JSON 错误处理、大文件上传内存风险和更系统化的前端测试覆盖。
- 章节分割 raw regex 保护、预览/实际分割一致性和结构化错误。
- 配置损坏备份、headless/frozen 环境提示、本地路径安全边界。
- 维护者文档、运行时规则文档、OpenSpec 到测试的映射和 archived changes 索引。
- 后续 LLM 聚合方案。

## 顶层结论

1. 原始审计报告保留发现时的风险描述；判断当前是否仍需处理时，以本文“当前跟进状态”和 [follow-up-backlog.md](follow-up-backlog.md) 为准。
2. `webui_backend/api_app.py` 的路由集中问题、`webui_backend/project_workspace.py` 的内部职责拆分、`frontend/src/views/TriggerScanPage.tsx` 的页面职责拆分和 `logic/utils.py` 的低层工具拆分均已完成；当前最大维护风险转向尚未覆盖的运行时持久化/恢复、文章总结 partial success 和章节分割一致性。
3. 任务终态和雷点扫描关键状态已经完成第一轮治理，但完整任务持久化、事件回放和后端重启恢复仍未覆盖。
4. 总结工作流剩余风险主要集中在文章总结 partial success、状态文件与输出文件 reconcile，以及重试次数语义澄清。
5. 文件与路径能力已有 ownership 删除保护和 Windows 打开目录体验优化，但自定义路径无效、headless/frozen 环境、路径安全边界和配置损坏提示仍需继续治理。

## 建议修复顺序

| 顺序 | 风险 | 复杂度 | 建议后续动作 |
| --- | --- | --- | --- |
| 1 | 文章总结 partial success 缺少明示 | M | 给部分失败结果增加状态、warning 和端到端断言 |
| 2 | 前端 API client 与大文件上传健壮性不足 | M | 优化非 JSON 错误处理、上传大小预检、统一 `apiClient` 路径，并在现有 Vitest 基础上补测试 |
| 3 | 章节分割 raw regex 与预览/实际一致性风险 | M | 抽共享章节边界解析器，补 regex 预检/限制和结构化错误返回 |
| 4 | 任务运行时缺少持久化和事件恢复 | L | 先持久化 terminal task summary，再设计 SSE heartbeat、事件回放和重启提示 |
| 5 | 本地路径与配置损坏提示不足 | M | 明确本地单用户边界，补 `.bak` 备份、UI warning 和本地能力不可用提示 |
| 6 | 维护者文档和 spec-to-test 映射不足 | S | 补 README 维护者章节、运行时规则文档和 archived changes 索引 |
| 7 | 后续 LLM 聚合方案未设计 | M | 单独设计 API 成本、JSON 解析、fallback 行为和 UI 披露 |

## 已知验证限制

- 未调用真实 LLM API，LLM 行为风险基于代码路径、测试替身和失败处理逻辑判断。
- 未启动浏览器做完整手工交互；前端已执行 Vitest、TypeScript 检查和生产构建。
- 未在打包后的 frozen 环境中验证 `run_gui.py`、本地文件选择器和静态资源托管。
