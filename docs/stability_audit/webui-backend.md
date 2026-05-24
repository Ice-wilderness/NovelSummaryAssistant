# WebUI 后端 API 与服务层审计

## 模块职责

后端位于 `webui_backend/`，主要提供 FastAPI 路由、配置读写、任务运行时、项目工作区、提示词工作流、雷点档案、章节模式配置、文件/路径服务。

## 关键入口

- `webui_backend/api_app.py`
- `webui_backend/task_runtime.py`
- `webui_backend/workflow_services.py`
- `webui_backend/project_workspace.py`
- `webui_backend/config_service.py`
- `webui_backend/config_models.py`
- `webui_backend/trigger_profile_service.py`
- `webui_backend/pattern_config_service.py`

## 发现

### 高风险：`api_app.py` 路由文件过大且内聚度低

- 现象：`webui_backend/api_app.py` 超过 1500 行，包含应用初始化、路径解析、项目解析、任务启动、雷点扫描、章节预览、文件上传、静态资源托管等职责。
- 证据：同一 `create_app` 闭包内定义了数十个路由和辅助函数，且直接引用多个服务对象。
- 影响：新增功能很容易修改同一文件，冲突概率高；测试虽覆盖多，但局部逻辑难以单独复用。
- 风险级别：高。
- 建议：按 `config_routes`、`project_routes`、`task_routes`、`trigger_scan_routes`、`chapter_routes` 拆分 APIRouter，同时保留现有路径契约。

### 高风险：任务运行时只保存在内存

- 现象：`TaskRuntime` 的 `_handles` 只存在进程内，`/api/tasks` 和 SSE 只读取内存任务记录。
- 证据：`TaskRuntime.__init__` 初始化普通 dict；没有任务记录持久化或启动恢复逻辑。
- 影响：后端重启后，前端无法查询旧任务事件；项目元数据可能仅保留 `latest_task_id/status`，与真实任务明细脱节。
- 风险级别：高。
- 建议：至少将 terminal task 摘要落盘，或者明确“任务事件只在当前进程有效”，前端按项目进度兜底展示。

### 高风险：取消语义在不同 runner 中不一致

- 现象：`TaskRuntime.cancel_task` 会 cancel asyncio task，但小说总结 orchestrator 捕获 `CancelledError` 后返回 `False`，可能被上层转成 failed。
- 证据：`logic/orchestrator.py` 在 `except asyncio.CancelledError` 中 `return False`；`create_novel_summary_runner` 把 false 转成 `"failed"`；`TaskRuntime` 只有收到传播出的 `CancelledError` 才标记 cancelled。
- 影响：用户点击取消后，项目和任务状态可能显示 failed，而不是 cancelled。
- 风险级别：高。
- 建议：让核心工作流重新抛出 `CancelledError`，并为小说总结、文章总结、分割、雷点扫描分别补取消语义测试。

### 中风险：SSE 事件流没有结束或心跳协议

- 现象：`/api/tasks/{task_id}/events` 的 stream 永久等待 `next_event`，terminal event 后不会由服务端主动结束。
- 证据：`api_app.py` 的 `stream()` 是无限循环。
- 影响：客户端必须自行关闭；断线和重连时没有 last-event-id 或事件回放协议。
- 风险级别：中。
- 建议：terminal event 后退出 stream，或实现心跳和基于任务 events 的回放。

### 中风险：部分错误被吞掉，诊断信息不足

- 现象：多个服务层逻辑使用宽泛 `except Exception: pass` 或转换成默认值。
- 证据：`workflow_services.py` 读取 pattern config 失败后直接忽略；`project_workspace.py` 读取 JSON 失败返回空 dict；`pattern_config_service.py` 配置损坏时重建默认配置。
- 影响：配置损坏或迁移失败可能表现为“设置丢失”，用户难以知道真实原因。
- 风险级别：中。
- 建议：对可恢复错误记录 warning，并在 API 响应或项目 warnings 中暴露。

## 优化空间

- 用 APIRouter 和服务依赖注入拆分 `create_app`。
- 为任务运行时补充状态持久化边界文档或实现。
- 为 `api_app.py` 的路径解析、上传、任务启动建立更细粒度单元测试，降低 E2E 测试压力。

## 验证

- `python -m pytest` 通过，包含 `test_api_app.py`、`test_task_runtime.py`、`test_project_workspace.py` 等后端主路径测试。
