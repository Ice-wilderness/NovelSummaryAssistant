## Why

`frontend/src/views/TriggerScanPage.tsx` 仍约 89 KB，单文件同时承载档案管理、扫描配置、任务启动、报告历史、finding 复核、上下文弹窗和多组派生状态。它已经是当前前端最高维护风险之一，先做无行为变化拆分可以降低后续雷点扫描功能修复和 UI 验证的冲突面。

## What Changes

- 将雷点扫描页面拆分为更小的组件、hooks 和纯工具模块，建议边界包括 profile 管理、scan config、report history/detail、finding review、context modal、result filters 和 display helpers。
- 保留现有 WebUI 用户行为：tab、字段、默认值、API 调用路径、任务控制、报告展示、warning 展示、剧透级别、复核动作和上下文查看都不改变。
- 引入最小前端测试基础，用于保护从大页面拆出的关键纯逻辑和轻量组件边界；优先采用与 Vite/React 生态匹配的 Vitest + Testing Library。
- 拆分完成后继续运行 `npm run build`，并新增/运行前端测试脚本。
- 不修改后端 API、雷点扫描数据模型、持久化报告格式或用户可见功能。

## Capabilities

### New Capabilities

- `trigger-scan-page-modularity`: 定义雷点扫描页面拆分后的内部边界、行为兼容要求和前端测试保护。

### Modified Capabilities

- None.

## Impact

- 主要影响 `frontend/src/views/TriggerScanPage.tsx`，并新增 `frontend/src/components/trigger-scan/`、`frontend/src/hooks/trigger-scan/` 或 `frontend/src/views/trigger-scan/` 等内部模块。
- 可能影响 `frontend/package.json` 和 `frontend/package-lock.json`，用于新增前端测试脚本和测试依赖。
- 预计新增前端测试文件，覆盖 display helpers、profile draft 操作、result filtering/pagination 或拆分出的核心组件。
- 不影响 FastAPI 路由、后端服务、OpenSpec 既有用户行为规格或运行时数据。
