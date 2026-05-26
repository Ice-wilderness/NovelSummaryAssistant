## Why

前端上传和请求错误处理仍有几处容易让用户遇到不可读错误或浏览器卡顿的边界：API client 在非 JSON 错误响应下会抛出裸解析异常，大文件上传会先在浏览器端完整读入内存，小说分割任务仍有一条原生 `fetch` 路径绕过统一错误模型。现在前端已有 Vitest 基础，适合用一个小而可验证的 change 把这些边界收敛起来。

## What Changes

- 优化前端 API client 的响应解析：非 JSON 错误响应应保留 HTTP status、status text 和短文本预览，并通过现有 `ApiError` 暴露。
- 在工作流文件上传入口增加前端大小预检，沿用后端单文件 100 MB 上限，在读取文件内容前给出可理解的错误。
- 将小说分割任务启动路径收敛到统一 `apiClient` 方法，避免页面内手写 `fetch`、JSON 解析和错误处理。
- 为 API client 非 JSON 错误、上传大小预检和小说分割任务启动 API 方法补 focused Vitest 覆盖。
- 不改变后端上传大小限制、上传 API URL、任务启动 API URL、项目工作区文件布局或已有用户操作流程。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `file-upload-workflow`: 上传控件在浏览器端读取文件前应执行与后端一致的大小预检，并以可操作错误阻止超限文件进入工作流。
- `webui-workbench`: WebUI 的统一 API client 应对非 JSON 错误响应提供可读错误；小说分割任务启动应复用统一 API client 错误模型。

## Impact

- 主要影响 `frontend/src/api/client.ts`、`frontend/src/hooks/useManagedProject.ts` 和 `frontend/src/views/NovelSummaryPage.tsx`。
- 预计新增或调整前端测试，覆盖 API client 错误解析、上传大小预检和 splitter task API 方法。
- 可能新增小型前端 helper 常量或函数，用于共享 100 MB 上传上限和用户提示。
- 不引入新依赖，不修改后端接口契约，不修改锁文件，除非现有测试脚本暴露出必要的配置缺口。
