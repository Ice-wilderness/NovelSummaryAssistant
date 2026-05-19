## Why

当前提示词页面只支持按模板 key 选择并编辑一段纯文本，无法对应小说总结、文章总结、自定义总结等实际工作流中的提示词节点，也无法让用户按消息角色、执行顺序和可复用模块来组织提示词。随着 WebUI 已经承载多个工作流，提示词配置需要从“文件级文本编辑”升级为“工作流级编排”，并补齐页面说明，降低用户误配置成本。

## What Changes

- 将提示词页面重构为按实际工作流分页的配置界面，每个工作流显示其参与的提示词节点和默认执行含义。
- 支持在每个工作流内编辑每个提示词节点，包含节点名称、说明、关联变量、消息序列和保存状态。
- 支持用户自定义单个提示词节点内的消息顺序，以及每条消息的角色（系统、用户、助手）和内容。
- 支持提示词模块化：用户可以维护可复用模块，并在节点消息中引用、插入或组合这些模块。
- 保持与现有 `prompt_cache` 文本文件的兼容迁移，确保已有提示词不会在重构后丢失或被静默覆盖。
- 为当前所有页面补全说明引导，让用户能理解按钮、配置项、状态展示、日志、工作流模块和提示词模块的用途。
- 实施时按小功能拆分，每完成一个可验证的小功能即提交一次 Git commit。

## Capabilities

### New Capabilities

- `workflow-prompt-composition`: 定义按工作流、提示词节点、消息角色/顺序和模块化组合管理提示词的行为。

### Modified Capabilities

- `configuration-management`: 将提示词管理从单段模板文本扩展为结构化提示词配置、模块库、兼容迁移、保存和重置行为。
- `webui-workbench`: 为提示词页面和现有所有工作流页面补充可理解的说明引导，并保持响应式布局可用。

## Impact

- 受影响前端：`frontend/src/views/PromptEditorPage.tsx`、各工作流页面、`frontend/src/state/AppState.tsx`、`frontend/src/api/types.ts`、`frontend/src/api/client.ts`、表单/说明组件与样式。
- 受影响后端：`webui_backend/config_models.py`、`webui_backend/config_service.py`、`webui_backend/api_app.py`，以及读取提示词的运行时路径。
- 受影响业务逻辑：`logic/prompts.py`、`logic/utils.py`、`logic/llm_api.py` 和各总结流程中使用提示词 key 的位置。
- 受影响测试：配置服务、API 路由、提示词加载/格式化、前端端到端或组件行为测试。
- 持久化影响：需要新增结构化提示词配置存储，同时保留对现有 `prompt_cache/*.txt` 的读取、迁移或回退能力。
