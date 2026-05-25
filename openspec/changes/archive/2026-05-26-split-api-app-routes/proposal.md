## Why

稳定性审计把 `webui_backend/api_app.py` 标为高风险维护热点：单个 `create_app` 闭包同时承载配置、项目、任务、雷点扫描、章节、文件路径和静态资源等路由职责，后续任意功能修复都容易扩大冲突面。

本变更先处理后端 API 路由拆分这一块，目标是在不改变外部 URL、响应语义和现有验证基线的前提下，把路由按职责移出超大文件，为后续前端拆分、任务持久化和章节分割修复降低维护成本。

## What Changes

- 将 `webui_backend/api_app.py` 中的后端 API 路由按职责拆分为更小的 APIRouter 或等价路由模块。
- 保留现有 API 路径、HTTP 方法、请求/响应结构、错误状态码和静态资源挂载行为。
- 保留 `create_app` 作为应用组装入口，使测试和启动脚本无需迁移到新入口。
- 为拆分后的路由注册和关键 API 路径补充或复用现有测试，确保拆分为无行为变化重构。
- 不新增依赖，不调整前端 API contract，不引入任务运行时持久化或新的用户可见功能。

## Capabilities

### New Capabilities

- `webui-api-route-modularity`: 约束 WebUI 后端 API 路由按职责模块化注册，并保持现有外部 API 契约不变。

### Modified Capabilities

- 无。

## Impact

- 主要影响：`webui_backend/api_app.py`、新增或调整的 `webui_backend/*_routes.py` / `webui_backend/routes/*` 模块、相关路由测试。
- 验证影响：优先运行后端 API 相关定向测试，再运行完整 Python 测试；如触及前端路径契约，补充 `npm run build`。
- 兼容性：不应产生 breaking change；现有前端、测试和本地启动方式应继续使用原 URL 契约。
