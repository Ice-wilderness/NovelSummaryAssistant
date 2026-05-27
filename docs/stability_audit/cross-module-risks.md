# 跨模块风险汇总

## 优先级 1：长任务控制语义不一致（已完成第一轮治理）

- 涉及模块：`TaskRuntime`、`workflow_services`、`logic/orchestrator.py`、`article_summary_logic.py`、`custom_summary_logic.py`、前端任务订阅。
- 现象：取消、暂停、失败在不同工作流中传播方式不同；雷点扫描暂停不阻塞，小说、文章、自定义总结取消可能显示 failed 或普通结果。
- 影响：用户无法可靠判断长任务是否真的停止；项目状态可能被错误记录。
- 原始风险级别：高。
- 当前状态：取消终态、雷点扫描暂停阻塞、雷点扫描与 summary 类任务的 `partial_failed` 展示、SSE 终态兜底、轻量任务摘要持久化和 `interrupted` 重启提示已完成；文章/自定义总结 partial result 会保留 warning 和失败输入详情。剩余风险集中在完整事件日志、`Last-Event-ID` 回放、SSE heartbeat 和 running task 自动恢复。
- 复杂度：M。
- 后续建议：如确实需要更强任务恢复，再单独设计完整事件日志、SSE heartbeat、`Last-Event-ID` 回放和 running task 恢复边界。

## 优先级 2：雷点扫描续扫与报告状态边界（已完成第一轮治理）

- 涉及模块：`workflow_services.py`、`logic/trigger_scan/scan_state.py`、`reporting.py`、前端报告轮询。
- 现象：续扫进度 total/completed 口径不一致；旧 findings 验证上下文可能缺失；部分失败可能显示 completed。
- 影响：用户可能误判扫描完成度和报告可信度。
- 原始风险级别：高。
- 当前状态：续扫计数、历史 finding 验证、`unverified` warning、`partial_failed` 和 `cancelled` 语义已治理；前端结果/复核 UI 已拆分并补 focused tests。
- 复杂度：M。
- 后续建议：保留当前 deterministic aggregation，后续 LLM 聚合另立设计；真实浏览器交互测试仍可补。

## 优先级 3：接口契约和实现漂移（已澄清核心漂移）

- 涉及模块：OpenSpec、提示词编辑器、`workflow_services.py`、`apiClient` 类型。
- 现象：聚合提示词被暴露为可编辑节点，但后端没有真正调用 LLM 聚合。
- 影响：用户编辑提示词后可能没有任何效果，维护者也会按错误假设开发。
- 原始风险级别：中。
- 当前状态：聚合提示词已澄清为当前 deterministic aggregation；`trigger-scan-page-modularity` 主规格已同步，记录页面拆分边界。
- 复杂度：M。
- 后续建议：继续建立 spec-to-test 映射，避免新规格再次和实现长期漂移。

## 优先级 3.5：总结 partial result 可信度（已治理）

- 涉及模块：`TaskRuntime`、`workflow_services.py`、`logic/article_summary_logic.py`、`logic/custom_summary_logic.py`、前端文章/自定义总结页面。
- 现象：文章 section 或自定义素材部分失败后仍可能产生可用结果，但此前缺少结构化 partial 状态、失败输入列表和用户可见 warning。
- 影响：用户可能误以为结果完整。
- 原始风险级别：中。
- 当前状态：文章总结和自定义总结已复用 `partial_failed`，保留可用结果、warning、失败 section/source file 详情，并通过 API、项目历史和前端页面展示。
- 当前风险级别：低。
- 后续建议：状态文件与输出文件 reconcile 仍需单独治理，避免导入旧项目或手工删除输出后出现进度误判。

## 优先级 3.75：章节分割边界一致性（已治理）

- 涉及模块：`logic/chapter_boundaries.py`、`logic/chapter_splitter.py`、`splitters/`、`ProjectWorkspaceService`、章节预览 API、前端分割页和小说总结页。
- 现象：raw regex 可能直接扫全文；预览和实际分割逻辑重复；失败原因容易折叠为 `(False, 0)`；小说总结源文件分割失败可能影响既有章节列表。
- 影响：用户可能按错误预览确认分割，或在失败后难以排查；高风险正则可能影响本地后端可用性。
- 原始风险级别：中。
- 当前状态：已新增共享章节边界解析和 `ChapterSplitError`；raw regex 在预览/实际分割前执行保守校验和预检；预览、实际写文件和标题列表模式共用边界结果；direct split、splitter task 和小说总结源文件分割会暴露可读失败原因；项目入库失败会保留既有 uploads。
- 当前风险级别：低。
- 后续建议：只在后续扩展更复杂 regex 能力时补充额外预检样本；配置损坏备份另归入配置治理。

## 优先级 4：文件/输出目录边界缺少 ownership（已治理核心删除风险）

- 涉及模块：项目工作区、用户设置、前端项目保存、上传预检、导出目录打开/迁移/删除。
- 现象：自定义输出目录可以指向任意本地目录；删除项目和迁移主要依赖路径和目录名判断。
- 影响：存在误删或误迁移用户文件的边界风险。
- 原始风险级别：高。
- 当前状态：系统管理的输出目录已有 ownership metadata，删除项目时只删除 ownership 匹配的输出目录；Windows 打开目录体验已优化；前端已在读取文件前执行 100 MB 上传大小预检。
- 复杂度：M。
- 后续建议：继续补自定义路径无效提示、headless/frozen 环境错误文案和本地路径安全边界。

## 优先级 5：诊断日志隐私与容量风险（已治理核心脱敏和保留策略）

- 涉及模块：LLM API、运行时缓存、项目输出。
- 现象：失败日志会保存输入消息、完整提示词和响应文本；没有大小和数量限制。
- 影响：可能保留用户原文、提示词和模型输出，长期运行会膨胀磁盘。
- 原始风险级别：中。
- 当前状态：API 失败诊断已保留完整非密钥输入/输出并脱敏敏感凭据，清理/保留路径已有测试；后续仍可按需要补 UI 开关或更细粒度容量提示。
- 复杂度：M。
- 后续建议：若真实使用中诊断目录增长过快，再加入可配置保留天数/大小和 UI 披露。

## 优先级 6：超大文件导致维护集中风险（已完成当前轮次）

- 涉及模块：后端 API、项目工作区、前端雷点页面、工具模块。
- 现象：`api_app.py` 路由拆分、`project_workspace.py` 服务拆分、`TriggerScanPage.tsx` 页面拆分和 `logic/utils.py` 低层工具拆分均已完成。
- 当前状态：`logic/utils.py` 已缩减为兼容门面，summary output、file IO、prompt runtime、progress events、text extraction、chapter naming、batching、API logging 和 chapter writing 等职责已拆入 focused modules。
- 影响：当前主要集中维护风险已显著降低；后续新增行为仍应优先进入对应 focused module，避免重新膨胀门面文件。
- 当前风险级别：低。
- 复杂度：L。
- 建议：不再把大模块拆分作为首要 backlog；后续只在某个 focused module 继续膨胀时再小步拆分，并以现有 Python 测试保护。
