# 项目稳定性与可维护性审计总览

本文是 `audit-project-stability-maintainability` 变更的总览报告。审计目标是覆盖项目主要模块，记录稳定性风险、潜在坑、可维护性问题、优化空间、验证结果和后续建议修复顺序。

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

## 验证基线

- `python -m pytest`：183 passed。
- `npm run build`：TypeScript 检查和 Vite 生产构建通过。

## 顶层结论

1. 当前测试和前端构建都能通过，说明已有功能的主路径具备一定保护。
2. 最大维护风险来自几个超大模块集中承载太多职责：`webui_backend/api_app.py`、`webui_backend/project_workspace.py`、`frontend/src/views/TriggerScanPage.tsx`、`logic/utils.py`。
3. 任务运行时状态主要驻留内存，项目元数据只保存最近任务状态；服务重启、SSE 断开、暂停/取消语义在不同工作流之间并不完全一致。
4. 雷点扫描是近期复杂度最高的新增能力，存在暂停不生效、续扫进度口径、聚合提示词契约漂移等需要优先复查的问题。
5. 小说、文章、自定义总结的取消和部分成功状态需要统一，否则用户很难区分“主动停止”“失败”和“生成了不完整产物”。
6. 文件与路径能力已经有上传限制、文件名清理和输出目录迁移保护，但仍允许用户配置任意本地输出目录，误删、误迁移和运行时文件膨胀风险需要治理。

## 建议修复顺序

| 顺序 | 风险 | 复杂度 | 建议后续动作 |
| --- | --- | --- | --- |
| 1 | 雷点扫描暂停/续扫语义不一致 | M | 新建 change 修复暂停等待、续扫进度统计、旧 finding 验证上下文 |
| 2 | 长任务取消在小说、文章、自定义总结路径可能被转成 failed 或普通结果 | S | 增加取消语义测试并让 `CancelledError` 贯穿到 `TaskRuntime` |
| 3 | 雷点扫描聚合提示词存在契约漂移 | M | 明确使用 deterministic 聚合或真正调用聚合 LLM，并同步 OpenSpec |
| 4 | 后端 API 和前端雷点页面过大 | L | 分阶段拆分路由、服务和页面组件，不改变外部行为 |
| 5 | API 失败诊断日志可能写入完整原文和提示词 | M | 引入大小限制、内容截断策略和可配置诊断开关 |
| 6 | 自定义输出目录的删除/迁移边界依赖目录命名 | M | 增加输出目录 ownership 标记和更强的删除保护 |
| 7 | 前端缺少组件级或交互级自动测试 | M | 为项目保存、任务事件、雷点扫描结果页补充前端测试策略 |
| 8 | 文章总结和雷点扫描缺少 partial success 明示 | M | 给部分失败结果增加状态、warning 和端到端断言 |

## 已知验证限制

- 未调用真实 LLM API，LLM 行为风险基于代码路径、测试替身和失败处理逻辑判断。
- 未启动浏览器做完整手工交互，只执行了前端 TypeScript 检查和生产构建。
- 未在打包后的 frozen 环境中验证 `run_gui.py`、本地文件选择器和静态资源托管。
