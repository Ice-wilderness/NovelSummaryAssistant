## Why

稳定性审计发现，本地配置损坏、自定义输出目录无效和本地路径能力不可用时，当前行为容易表现为静默回退或诊断不足。现在需要把项目定位明确为本地单用户应用，并让配置恢复、输出目录选择和打开目录操作都以用户可理解、可确认的方式失败或回退。

## What Changes

- 明确 WebUI 的本地路径能力面向本地单用户场景；当文件选择器、目录选择器或打开目录能力在 headless、缺少 GUI 依赖、frozen 打包等环境不可用时，后端返回可操作错误，前端在对应页面局部展示。
- 保存或启动任务时，项目级自定义输出目录无效不再静默回退默认目录；后端返回明确验证错误，前端提供“使用默认输出目录”的显式按钮供用户选择。
- 读取旧 metadata 或历史项目时仍保持兼容：遇到无效旧自定义输出目录可以回退默认目录，但必须返回 warning，避免阻塞历史项目加载。
- 配置文件损坏时，后端在恢复默认值前备份损坏文件为 `.bak`，并返回对应配置域的 warning；前端在 API 设置、用户设置或章节模式等对应页面局部展示。
- `open_directory` 仅允许打开当前项目有效输出目录，且失败时返回可显示的错误；不再作为任意本地路径打开能力。
- 补充 focused tests，覆盖无效自定义输出目录、默认目录回退确认、配置损坏备份/warning、本地能力不可用提示和输出目录打开边界。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `configuration-management`: 扩展配置损坏恢复契约，要求备份损坏文件、返回对应配置域 warning，并在相关设置页面局部展示。
- `managed-project-outputs`: 扩展自定义输出目录验证和打开输出目录契约，要求无效路径显式报错、用户确认后才回退默认目录，并限制 `open_directory` 到有效输出目录。
- `webui-workbench`: 扩展前端工作台契约，要求局部展示配置/路径 warning，并为无效自定义输出目录提供“使用默认输出目录”的显式操作。

## Impact

- 后端：`webui_backend/config_service.py`、用户设置/章节模式加载逻辑、`webui_backend/project_workspace.py` 及 `workspace_services/`、`webui_backend/file_services.py`、路径/目录 API routes、任务启动前项目保存与输出目录解析。
- 前端：设置页、章节模式相关页面或控件、项目输出目录控件、历史项目/项目详情 warning 展示、打开输出目录操作、API client 类型。
- 数据兼容：旧项目和旧 metadata 继续可加载；兼容回退仅用于读取既有数据，并必须携带 warning。
- 用户体验：主动保存或启动任务时不再静默改写输出目标；用户可以在错误提示中显式选择回退默认目录。
- 测试：新增或扩展 `tests/test_config_service.py`、`tests/test_project_workspace.py`、`tests/test_api_app.py`，以及对应前端 Vitest focused tests。
