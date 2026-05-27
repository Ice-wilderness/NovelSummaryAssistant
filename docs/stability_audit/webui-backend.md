# WebUI 后端 API 与服务层审计

## 模块职责

后端位于 `webui_backend/`，主要提供 FastAPI 路由、配置读写、任务运行时、项目工作区、提示词工作流、雷点档案、章节模式配置、文件/路径服务。

## 关键入口

- `webui_backend/api_app.py`
- `webui_backend/routes/`
- `webui_backend/task_runtime.py`
- `webui_backend/workflow_services.py`
- `webui_backend/project_workspace.py`
- `webui_backend/workspace_services/`
- `webui_backend/config_service.py`
- `webui_backend/config_models.py`
- `webui_backend/trigger_profile_service.py`
- `webui_backend/pattern_config_service.py`

## 发现

### 已治理：`api_app.py` 路由文件过大且内聚度低

- 现象：`webui_backend/api_app.py` 超过 1500 行，包含应用初始化、路径解析、项目解析、任务启动、雷点扫描、章节预览、文件上传、静态资源托管等职责。
- 证据：同一 `create_app` 闭包内定义了数十个路由和辅助函数，且直接引用多个服务对象。
- 影响：新增功能很容易修改同一文件，冲突概率高；测试虽覆盖多，但局部逻辑难以单独复用。
- 原始风险级别：高。
- 当前状态：`api_app.py` 已缩减为应用组装入口，当前约 428 行；公开路由拆入 `webui_backend/routes/`，并通过 route parity 测试保护公开 method/path 契约。
- 后续建议：新增 API 时优先进入对应 route module；只有共享上下文或静态前端 fallback 需要改 `api_app.py`。

### 已部分治理：任务运行时只保存在内存

- 现象：`TaskRuntime` 的 `_handles` 只存在进程内，`/api/tasks` 和 SSE 只读取内存任务记录。
- 证据：`TaskRuntime.__init__` 初始化普通 dict；没有任务记录持久化或启动恢复逻辑。
- 影响：后端重启后，前端无法查询旧任务事件；项目元数据可能仅保留 `latest_task_id/status`，与真实任务明细脱节。
- 原始风险级别：高。
- 当前状态：`persist-task-terminal-summaries` 已将轻量任务摘要落盘；终态任务在后端重启后仍可通过任务 API 查询，非终态任务会恢复为 `interrupted` 并向前端/项目历史暴露可操作提示。完整事件日志、`Last-Event-ID` 回放、SSE heartbeat 和自动恢复 running task 仍未实现。
- 当前风险级别：中。
- 后续建议：如需更完整恢复能力，再单独设计事件日志落盘、heartbeat、回放协议和 running task 恢复边界。

### 已治理：取消语义在不同 runner 中不一致

- 现象：`TaskRuntime.cancel_task` 会 cancel asyncio task，但小说总结 orchestrator 捕获 `CancelledError` 后返回 `False`，可能被上层转成 failed。
- 证据：`logic/orchestrator.py` 在 `except asyncio.CancelledError` 中 `return False`；`create_novel_summary_runner` 把 false 转成 `"failed"`；`TaskRuntime` 只有收到传播出的 `CancelledError` 才标记 cancelled。
- 影响：用户点击取消后，项目和任务状态可能显示 failed，而不是 cancelled。
- 原始风险级别：高。
- 当前状态：主要业务 runner 已统一传播用户取消并由 `TaskRuntime` 标记为 `cancelled`，相关 workflow service 和 task runtime 测试已覆盖。
- 后续建议：新增长任务 runner 时必须保留 `CancelledError` 传播，避免把用户取消包装成普通失败。

### 已部分治理：SSE 事件流没有结束或心跳协议

- 现象：`/api/tasks/{task_id}/events` 的 stream 永久等待 `next_event`，terminal event 后不会由服务端主动结束。
- 证据：`api_app.py` 的 `stream()` 是无限循环。
- 影响：客户端必须自行关闭；断线和重连时没有 last-event-id 或事件回放协议。
- 原始风险级别：中。
- 当前状态：服务端 task event stream 已在 terminal event 后结束，前端也会在 SSE 断开后拉取任务状态兜底；已落盘终态或 `interrupted` 任务的事件流会暴露最终状态并关闭。尚未实现 heartbeat、last-event-id 或完整持久化事件回放。
- 后续建议：若要支持完整事件恢复或自动恢复 running task，再设计任务事件落盘、heartbeat、回放协议和执行恢复边界。

### 已治理：summary 类任务缺少结构化部分失败结果

- 现象：文章总结和自定义总结此前只能通过普通字符串结果或失败字符串表达终态，无法把“有可用结果但部分输入失败”的信息结构化传给任务状态 API 和项目历史。
- 当前状态：`TaskRuntime` 已支持 `TaskRunOutcome`，summary runner 可以返回 `partial_failed`、warnings 和 `result_data`；文章总结和自定义总结的 partial result 会通过 `/api/tasks/{task_id}`、任务事件和项目历史保留，旧字符串 runner 行为保持兼容。
- 验证：`tests/test_task_runtime.py` 覆盖结构化 `partial_failed` 终态、事件和序列化；`tests/test_workflow_services.py` 与 `tests/test_api_app.py` 覆盖文章/自定义 summary partial response 和项目历史状态。
- 后续建议：新增业务 runner 时优先返回结构化 outcome，避免把业务状态编码进字符串。

### 已部分治理：部分错误被吞掉，诊断信息不足

- 现象：多个服务层逻辑使用宽泛 `except Exception: pass` 或转换成默认值。
- 证据：`workflow_services.py` 读取 pattern config 失败后直接忽略；`project_workspace.py` 读取 JSON 失败返回空 dict；`pattern_config_service.py` 配置损坏时重建默认配置。
- 影响：配置损坏或迁移失败可能表现为“设置丢失”，用户难以知道真实原因。
- 原始风险级别：中。
- 当前状态：API 失败诊断已补敏感信息脱敏和保留/清理路径；项目输出目录保留原因会回传给 WebUI；章节分割边界解析和 raw regex 保护会通过 `ChapterSplitError` 暴露可读失败原因。配置损坏备份、pattern config 重置 warning、导入/状态 reconcile warning 仍未系统化。
- 后续建议：对配置损坏、迁移回退和本地能力不可用继续补用户可见 warning。

### 已治理：章节分割失败缺少结构化错误传播

- 现象：章节预览、direct split、splitter task 和小说总结源文件分割此前容易把具体分割失败折叠为通用失败。
- 当前状态：预览 API、direct split 和小说总结源文件分割会返回明确 400 detail；splitter task 会把分割失败原因写入 task error；项目入库失败先发生在临时目录，不会清空既有 uploads。
- 验证：`tests/test_api_app.py` 覆盖预览无匹配、raw regex 高风险拒绝、direct split 失败和小说总结源文件分割失败保留项目；`tests/test_workflow_services.py` 覆盖 splitter runner 保留失败原因；`tests/test_project_workspace.py` 覆盖 split-and-ingest 失败保留 uploads。

## 优化空间

- 继续让 `api_app.py` 只承担应用组装、共享上下文和静态前端 fallback，避免把业务路由写回主入口。
- 在轻量任务摘要持久化基础上，按真实需求补充完整事件日志、SSE heartbeat 或 running task 恢复方案。
- 为路径解析、上传、任务启动和本地能力不可用补更细粒度单元测试，降低 E2E 测试压力。

## 验证

- `python -m pytest` 通过，当前基线为 254 passed，包含 `test_api_app.py`、`test_task_runtime.py`、`test_project_workspace.py` 等后端主路径测试。
- `test_api_app.py` 覆盖 route table parity、terminal SSE stream 行为、summary partial task response/project history、持久化终态任务查询、`interrupted` 中断状态和项目历史恢复。
