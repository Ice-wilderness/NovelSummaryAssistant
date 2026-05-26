## Context

稳定性审计将前端 API client、上传入口和小说分割页面列为下一轮优先治理项。当前 `frontend/src/api/client.ts` 在检查 `response.ok` 前直接 `JSON.parse` 响应文本，遇到 HTML、纯文本或空错误响应时会把真实 HTTP 状态隐藏在解析异常后面。`useManagedProject.uploadFiles` 和 `NovelSummaryPage.handleSourceUpload` 会先 `arrayBuffer()` 读取完整文件，再解码并发送或预览；后端已有 100 MB 单文件上限，但前端没有在读取前阻止超限文件。`NovelSummaryPage.confirmSplitAndIngest` 仍手写 `/api/tasks/splitter` 的 `fetch` 调用，和 `apiClient.startSplitter` 的统一错误模型漂移。

本 change 限定为前端边界加固和 focused tests。后端 API、上传大小上限、项目工作区布局、任务 runtime 和用户操作流程保持不变。

## Goals / Non-Goals

**Goals:**

- 让 API client 对 JSON 和非 JSON 错误响应都返回可读、包含 HTTP status 的 `ApiError`。
- 在前端读取上传文件内容前执行 100 MB 单文件预检，避免超限文件造成浏览器内存压力。
- 让小说分割任务启动复用 `apiClient.startSplitter`，不再在页面内维护独立错误解析逻辑。
- 用现有 Vitest 基础补 focused tests，覆盖本 change 的主要行为边界。

**Non-Goals:**

- 不改变后端 100 MB 限制，也不实现 multipart 或 streaming 上传。
- 不改上传 API、任务 API、项目 metadata 或任务记录 schema。
- 不重做上传控件 UI 或项目保存流程。
- 不把任务事件恢复、SSE heartbeat 或后端重启恢复纳入本 change。

## Decisions

1. 在 API client 内集中处理响应解析。

   `requestJson` 应先读取响应文本，再根据内容和 `Content-Type` 尝试解析 JSON。解析失败时，成功响应仍应暴露为明确错误，错误响应则使用 status text 或文本预览构造 `ApiError`。这样所有调用方都能复用同一错误模型。

   备选方案是在每个页面捕获 `SyntaxError` 并改写提示。它会继续复制错误处理逻辑，且无法覆盖未来新增 API 方法。

2. 前端大小预检使用共享常量，先阻止再读取。

   上传入口应共享 `MAX_UPLOAD_FILE_BYTES = 100 * 1024 * 1024` 一类常量，并在 `file.arrayBuffer()` 前检查 `file.size`。这不会降低后端校验的重要性，只是在浏览器端提前给用户更快、更清楚的反馈。

   备选方案是只依赖后端拒绝。该方案仍会让浏览器先读取和编码大文件，无法解决本次内存风险。

3. 保持现有文本解码策略，只移动边界检查。

   本 change 不改变 UTF-8 优先、GBK fallback 的解码行为；实现时可以抽出小型 helper 减少重复，但不为了单次复用建立复杂抽象。

   备选方案是同时重写上传编码检测。它会扩大回归面，和本次目标不匹配。

4. 小说分割任务调用使用已有 `apiClient.startSplitter`。

   `NovelSummaryPage.confirmSplitAndIngest` 已经导入 `apiClient`，且 API client 已有 `startSplitter` 方法。页面应调用该方法并继续保留现有成功后的项目刷新、源文件清理和预览清理行为。

   备选方案是保留原生 `fetch` 但复用一个局部 parser。这样仍会留下两套任务启动路径。

## Risks / Trade-offs

- 非 JSON 成功响应被当作错误暴露 -> 当前 API client 的泛型调用都期望 JSON；用定向测试固定成功 JSON、错误 JSON、错误文本三类行为。
- 文本预览可能过长或包含换行 -> 对非 JSON 错误详情做长度截断和空白规整，避免 UI 错误提示过大。
- 前端 100 MB 常量与后端限制未来漂移 -> 在常量注释或命名中注明与后端上传限制一致，并在规格里保留“与后端一致”的约束。
- 大文件预检只解决单文件读取前风险 -> 本 change 不做批量总大小或 streaming；后端仍负责最终校验。
- 抽 helper 可能造成过度设计 -> 只抽共享常量和必要的小函数，保持改动贴近现有页面/hook。

## Migration Plan

1. 为 `requestJson` 增加 JSON/非 JSON 错误解析逻辑，并补 API client tests。
2. 增加共享上传大小限制和预检 helper，在 `useManagedProject.uploadFiles` 与 `NovelSummaryPage.handleSourceUpload` 中读取前调用，并补测试。
3. 将 `NovelSummaryPage.confirmSplitAndIngest` 切换为 `apiClient.startSplitter`，保持请求 payload 和后续 UI 状态更新不变。
4. 运行前端 focused tests、`npm run test` 和 `npm run build`。

回退策略是恢复前端调用与 helper 改动；没有后端数据迁移。

## Open Questions

- 无。用户已确认前端大小预检沿用后端 100 MB 上限。
