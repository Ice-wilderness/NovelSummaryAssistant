# 前端工作台审计

## 模块职责

前端位于 `frontend/src/`，使用 React + TypeScript + Vite。核心职责包括页面导航、API 配置、提示词编辑、项目上传/保存、长任务控制、实时日志、章节分割预览和雷点扫描结果复核。

## 关键入口

- `frontend/src/App.tsx`
- `frontend/src/state/AppState.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/hooks/useManagedProject.ts`
- `frontend/src/hooks/useTaskActions.ts`
- `frontend/src/views/NovelSummaryPage.tsx`
- `frontend/src/views/TriggerScanPage.tsx`
- `frontend/src/views/trigger-scan/`
- `frontend/src/views/PromptEditorPage.tsx`

## 发现

### 已缓解：雷点扫描页面职责过度集中

- 现象：`frontend/src/views/TriggerScanPage.tsx` 约 90 KB，单文件同时管理档案 CRUD、扫描配置、预检、任务启动、报告轮询、结果过滤、剧透级别、上下文弹窗和导入导出。
- 证据：该文件包含大量 `useState`、`useEffect`、`useMemo` 和事件处理逻辑，状态定义从项目、档案、扫描配置延伸到报告详情和分页过滤。
- 影响：任一小改动都容易影响多个状态域；后续修复雷点扫描缺陷时，回归面很大。
- 原始风险级别：高。
- 当前状态：`split-trigger-scan-page` 已完成并归档，`TriggerScanPage.tsx` 约 1011 行，主要承担状态、effects、API handlers 和 tab composition；具体 UI/纯逻辑已拆到 `frontend/src/views/trigger-scan/`。
- 维护入口：profile 管理看 `ProfileTab.tsx` / `profileDraft.ts`，扫描配置看 `ScanConfigTab.tsx`，结果/复核看 `ResultsTab.tsx` / `resultFilters.ts`，上下文弹窗看 `ContextModal.tsx`，展示文案和 warning 看 `display.ts`。
- 后续建议：新增行为时优先在对应 focused module 内修改；只有某个状态域继续膨胀时，再从主页面抽 hook。

### 中风险：任务事件订阅缺少恢复策略

- 现象：`useTaskActions.ts` 使用模块级 `subscriptions` map 订阅 SSE，事件流错误时只设置全局错误，不自动拉取最新任务状态。
- 证据：`subscribeTaskEvents` 的 `onerror` 只调用 `handlers.onError`；`watchTask` 只在 terminal event 后调用 `getTask`。
- 影响：网络抖动或后端重启后，前端可能停留在旧状态，项目状态刷新依赖终态事件，用户可能不知道任务实际结果。
- 风险级别：中。
- 建议：SSE 错误后增加一次 `getTask` 兜底刷新，并考虑对 running task 做低频轮询兜底。

### 中风险：API client JSON 解析过于乐观

- 现象：`requestJson` 总是先 `JSON.parse(text)`，即使响应是非 JSON 错误页也会抛出裸 `SyntaxError`。
- 证据：`frontend/src/api/client.ts` 在检查 `response.ok` 前解析响应文本。
- 影响：后端代理、静态资源缺失或服务器错误返回 HTML 时，用户看到的错误不可读，也难以定位 API 状态码。
- 风险级别：中。
- 建议：先按 content-type 或 try/catch 解析；非 JSON 时仍抛 `ApiError(status, response.statusText/text preview)`。

### 中风险：上传文件在浏览器端完整读入内存

- 现象：`useManagedProject.uploadFiles` 和 `NovelSummaryPage.handleSourceUpload` 都通过 `file.arrayBuffer()` 完整读取文件，再转成字符串传给后端。
- 证据：上传限制在后端是 100 MB 单文件/批次，但前端读入会形成 ArrayBuffer 和字符串双份内存。
- 影响：大 TXT 可能造成浏览器卡顿或崩溃，尤其整本小说源文件分割路径。
- 风险级别：中。
- 建议：在前端增加文件大小预检和用户提示；长期可改为 multipart/stream 上传。

### 中风险：小说页绕过统一 API client

- 现象：`NovelSummaryPage.confirmSplitAndIngest` 使用原生 `fetch("/api/tasks/splitter")`，其余请求走 `apiClient`。
- 证据：该函数手写 JSON、错误解析和返回处理。
- 影响：错误处理、类型约束和后续接口变更容易漂移。
- 风险级别：中。
- 建议：把该请求收敛进 `apiClient.startSplitter` 或新增专用方法，并复用 `ApiError`。

### 低风险：提示词编辑器依赖 JSON.stringify 比较脏状态

- 现象：`PromptEditorPage` 通过 `JSON.stringify(draftMessages) !== JSON.stringify(selectedNode.messages)` 判断脏状态。
- 证据：模块和节点草稿都使用 stringify 比较。
- 影响：字段顺序或运行时补默认值可能造成误判；目前数据结构简单，风险可控。
- 风险级别：低。
- 建议：后续如字段增多，改用规范化比较函数。

## 优化空间

- 为 `useManagedProject`、`useTaskActions`、`requestJson` 补充前端单元测试。
- 沿用现有 Vitest + Testing Library 基础，为 API client、上传大小预检、任务订阅兜底和关键页面流补 focused tests。
- 将上传编码判断逻辑抽成共享工具，避免小说页和项目 hook 重复。

## 验证

- `npm run test` 通过，覆盖雷点扫描 display/filter/profile/config/results/context 拆分边界。
- `npm run build` 通过，TypeScript 和 Vite 构建未发现类型错误。
