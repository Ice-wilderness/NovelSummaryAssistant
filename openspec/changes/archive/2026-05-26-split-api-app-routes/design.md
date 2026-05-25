## Context

`webui_backend/api_app.py` 目前约 1600 行，`create_app` 闭包内包含应用状态初始化、服务工厂、请求解析辅助函数、路由处理器、任务事件流和前端静态资源 fallback。稳定性审计将它列为高风险维护热点，主要问题不是当前 API 行为错误，而是单文件承载过多职责，导致后续修复容易互相冲突。

本次变更是无行为变化重构。外部调用者仍通过 `create_app(...)` 创建 FastAPI 应用；前端仍使用现有 `/api/...` 路径；测试仍以当前 API contract 为准。

## Goals / Non-Goals

**Goals:**

- 将 `api_app.py` 内的 API 路由按职责拆为更小的路由注册模块。
- 保持现有 URL、HTTP 方法、请求/响应结构、错误状态码、任务状态语义和静态资源行为不变。
- 让拆分后的路由继续共享同一个 `TaskRuntime`、配置路径、运行时目录、项目服务和提示词缓存。
- 以现有后端 API 测试为主要回归保护，并为路由注册完整性补充轻量测试。
- 按功能块分阶段提交，便于审查和回退。

**Non-Goals:**

- 不实现任务持久化、SSE 事件回放或后端重启恢复。
- 不拆分前端 `TriggerScanPage.tsx`。
- 不改变项目工作区、雷点扫描、章节分割或总结工作流的业务语义。
- 不修改前端 API client contract，除非测试发现已有路径契约需要同步类型。
- 不新增依赖或更换 Web 框架。

## Decisions

1. 使用 `webui_backend/routes/` 包承载路由注册函数。

   每个模块暴露 `register_<domain>_routes(app, context)` 或返回 `APIRouter` 的等价接口，按配置/提示词、档案与模式、项目与上传、雷点扫描、总结与分割任务、任务运行时等职责拆分。选择子包而不是继续堆在 `webui_backend/` 根目录，是为了让路由文件集中管理，并避免和服务层模块混在一起。

   备选方案是只把部分路由移动到 `api_app_*.py` 平级文件。该方案改动更少，但长期会让根目录继续增长，边界不够清晰。

2. 保留 `create_app` 作为唯一应用组装入口。

   `create_app` 继续初始化 `app.state`、创建 FastAPI 实例、注册所有 API 路由、挂载前端静态资源，并保留测试可注入参数。这样启动脚本、测试和外部调用不需要迁移。

   备选方案是引入新的 application factory 或依赖注入容器。当前项目没有这类模式，新增抽象会超过本次无行为重构需要。

3. 引入轻量共享上下文，而不是让路由模块各自读取全局配置。

   路由模块需要访问 `TaskRuntime`、配置路径、项目服务工厂、触发档案服务、章节模式服务、任务可用性检查和若干请求解析函数。设计上通过一个内部 context 对象或 dataclass 从 `create_app` 传入，确保所有路由使用同一套 app state 和测试注入值。

   备选方案是在每个路由中通过 `request.app.state` 直接取值。这样可以减少参数传递，但会让路由函数更难单元测试，也更容易遗漏当前闭包里的共享辅助逻辑。

4. 先搬低耦合路由，再搬高耦合长任务路由。

   配置、提示词、模型、档案、章节模式等路由依赖较少，适合作为第一批；项目/上传和雷点扫描依赖项目服务与报告 store，放在中间；总结、分割和任务运行时路由涉及 `TaskRuntime`、runner 包装和 SSE，最后拆分。每批完成后运行对应定向测试并提交。

   备选方案是一次性整体搬迁。它能更快缩短文件，但审查困难，失败时也更难定位是哪组路由漂移。

## Risks / Trade-offs

- 路由注册遗漏 → 增加 route table parity 测试，比较拆分后应用必须暴露的关键 method/path 集合。
- 共享闭包辅助函数迁移后行为漂移 → 先只移动路由和必要 helper，避免同时重写业务逻辑；每批运行 `tests/test_api_app.py` 的相关用例。
- `app.state` 或服务工厂不一致 → 通过统一 context 传递路径和服务工厂，避免路由模块自行创建默认 runtime base path。
- SSE 和长任务路由较敏感 → 最后拆分，并额外运行 `tests/test_task_runtime.py` 与任务启动相关 API 测试。
- 文件数量增加带来导航成本 → 使用清晰的 `routes/` 包和领域命名，避免为单个端点创建过细文件。

## Migration Plan

1. 新增 `webui_backend/routes/` 包和共享 context，先不改变路由行为。
2. 分批移动低耦合 API 路由并运行定向测试。
3. 分批移动项目、雷点扫描、总结/分割和任务运行时路由，每批运行对应测试并提交。
4. 清理 `api_app.py` 中仅因迁移产生的未使用 import/helper，确认 `create_app` 仍是统一入口。
5. 运行完整 `python -m pytest`；如 API 类型或前端路径被触及，再运行 `npm run build`。

回退策略是按功能块提交逐个 revert；由于不改变数据模型和外部 contract，不需要运行时迁移。

## Open Questions

- 路由模块最终命名以实现时最小 diff 为准：可以从 `config_routes.py`、`project_routes.py` 等少数文件开始，避免过早拆得太碎。
- 若迁移过程中发现某个 helper 实际属于服务层，是否同步下沉到服务模块需要在实现时谨慎判断；默认只移动为路由共享 helper，不做业务层重构。
