## Context

`webui_backend/project_workspace.py` 目前是项目工作区的集中实现点，包含项目命名、metadata 读写、上传文件存储、输出目录解析与 ownership、导入旧项目识别、输出迁移、删除保护、进度扫描和本地目录打开等职责。稳定性审计将该文件列为下一轮最高优先级之一，核心问题是维护风险，而不是当前用户可见行为缺陷。

本 change 是无行为变化重构。现有 FastAPI 路由仍通过 `ProjectWorkspaceService` 使用项目工作区能力，前端仍通过现有 API 路径工作，既有 workspace/export 文件布局和 metadata 兼容性必须保持。

## Goals / Non-Goals

**Goals:**

- 将 `project_workspace.py` 中可独立理解和验证的职责拆到内部 helper 模块。
- 保留 `webui_backend.project_workspace` 作为稳定公开导入入口。
- 保持上传、项目保存/加载、导入识别、输出目录解析、输出迁移、删除保护、进度扫描和目录打开行为不变。
- 以现有 `tests/test_project_workspace.py` 和相关 API 测试作为主要回归保护，并在拆分边界增加必要的轻量断言。
- 按功能块提交，每个提交只包含一个可独立验证的拆分边界。

**Non-Goals:**

- 不实现任务运行时持久化、事件回放或后端重启恢复。
- 不处理文章总结 partial success、状态文件与输出文件 reconcile、raw regex 保护或前端大文件上传内存风险。
- 不修改 WebUI API contract、前端调用路径、持久化数据格式或工作区目录布局。
- 不新增依赖，不引入新的框架级服务容器。
- 不拆分 `TriggerScanPage.tsx` 或 `logic/utils.py`；它们保留为后续独立 change。

## Decisions

1. 保留 `project_workspace.py` 作为兼容门面。

   `ProjectWorkspaceService`、`ProjectMetadata`、`UploadedFileRef`、`sanitize_project_name`、`workflow_export_subdir`、`MAX_UPLOAD_FILE_BYTES` 等现有导入入口继续从 `webui_backend.project_workspace` 暴露。实现时可以把部分模型或 helper 移到内部模块，但必须在门面中 re-export 或保持原定义，避免调用方迁移。

   备选方案是把 `project_workspace.py` 直接替换成同名 package。该方式可能影响 Python import 解析和测试 mock 路径，收益不足，暂不采用。

2. 使用内部 helper 包按职责拆分，而不是一次性重写服务类。

   建议新增类似 `webui_backend/workspace_services/` 的内部包，按 metadata、uploads、outputs、imports、progress、local_open 等职责承载纯函数或小型 helper。`ProjectWorkspaceService` 继续负责编排这些 helper，并保持实例属性、路径注入和调用语义稳定。

   备选方案是把每组职责都改成独立服务类并引入依赖注入。当前项目没有这类模式，直接引入会让无行为重构变大，也会增加测试迁移成本。

3. 先拆低状态 helper，再拆依赖服务状态的流程。

   优先移动纯函数、扫描函数和 OS 打开函数，再移动输出 ownership、上传解析、导入识别、输出迁移和删除保护。每一步只下沉已经有测试覆盖或能快速补测的逻辑，避免在移动代码时同时改变业务判断。

   备选方案是按文件长度最大的方法先拆。它能更快缩短主文件，但更容易把相互依赖的状态迁移混在一起，失败时定位成本高。

4. 以行为回归测试确认拆分，而不是为每个 helper 新建大量实现细节测试。

   本次目标是保持外部行为不变，因此优先运行现有 project workspace 和 API 测试。只有当 helper 边界暴露出新风险，例如 import re-export、ownership 判定或 OS 打开 mock 路径变化时，才补充聚焦测试。

   备选方案是为所有新 helper 建立细粒度单元测试。它会带来大量与实现结构绑定的测试，后续继续拆分时维护成本偏高。

## Risks / Trade-offs

- 公开 import 路径漂移 -> 保留 `webui_backend.project_workspace` 门面，并运行现有 import/API 测试。
- 输出目录删除或 ownership 判断漂移 -> 每次移动 output/delete 逻辑后运行 project workspace 删除保护相关测试。
- 旧项目导入识别回归 -> 拆导入和 progress 逻辑后运行 legacy/import/granularity 相关测试。
- mock patch 路径失效 -> 目录打开函数迁移时同步调整测试或在门面保留可 patch 的兼容符号。
- 拆分过细导致导航成本上升 -> 按职责聚合 helper，避免为单个方法创建单独文件。

## Migration Plan

1. 新增内部 helper 包和最小 re-export 保护，确认现有导入路径可用。
2. 拆出纯函数、JSON/file 统计和进度扫描 helper，运行 `python -m pytest tests/test_project_workspace.py`。
3. 拆出输出目录、ownership、迁移和删除保护 helper，运行 project workspace 删除/迁移相关测试。
4. 拆出上传、导入识别和本地目录打开 helper，运行 project workspace 与 API 上传/打开目录相关测试。
5. 清理 `project_workspace.py` 中由本次拆分产生的未使用 import/helper，运行完整 `python -m pytest`；如触及前端 API 类型或构建路径，再运行 `npm run build`。

回退策略是按功能块提交逐个 revert。由于不改变数据格式、API contract 或目录布局，不需要运行时迁移。

## Open Questions

- 实现时 helper 包名称以最小 diff 为准；默认倾向 `webui_backend/workspace_services/`，除非现有命名显示更自然的边界。
- 如果拆分过程中发现某个行为本身有缺陷，默认只记录为后续事项，不在本 change 中修复，除非它阻塞无行为拆分。
