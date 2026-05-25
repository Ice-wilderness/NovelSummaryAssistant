## Why

`webui_backend/project_workspace.py` 已承担项目元数据、上传文件、输出目录、导入识别、删除保护、进度扫描和本地目录打开等多类职责，当前文件规模过大，后续稳定性修复很容易在同一模块中互相干扰。

稳定性审计已将大模块拆分列为下一轮最高优先级；本次 change 先聚焦项目工作区服务，作为无行为变化重构，为后续处理状态 reconcile、路径边界和配置损坏提示降低修改风险。

## What Changes

- 将项目工作区服务按职责拆分为更小的内部模块，例如元数据读写、上传引用解析、输出目录/ownership、导入识别、进度扫描和本地目录打开。
- 保留 `ProjectWorkspaceService`、`ProjectMetadata`、`UploadedFileRef`、`sanitize_project_name` 等现有公开导入入口，避免现有 API 路由、测试和调用方改用新路径。
- 保持现有 WebUI API method/path、请求/响应结构、状态码语义、工作区文件布局和输出目录 ownership 行为不变。
- 为拆分后的边界补充针对性回归测试，确保上传、导入、输出迁移、删除保护、进度识别和目录打开行为不漂移。
- 不新增运行时依赖，不更改持久化数据格式，不处理新的用户可见功能。

## Capabilities

### New Capabilities

- `project-workspace-service-modularity`: 定义项目工作区服务拆分后的内部职责边界、公开兼容入口和无行为变化验证要求。

### Modified Capabilities

- None.

## Impact

- 主要影响 `webui_backend/project_workspace.py` 及新拆出的 `webui_backend/` 内部工作区 helper 模块。
- 相关测试集中在 `tests/test_project_workspace.py` 和覆盖项目工作区 API 行为的 `tests/test_api_app.py`。
- 不影响前端调用路径、FastAPI 公开路由、OpenSpec 既有用户行为规格或第三方依赖。
