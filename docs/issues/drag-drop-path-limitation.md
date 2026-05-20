# 拖拽导入路径能力与限制

## 状态

旧的“拖拽/填写本地文件路径”方案已停用。当前工作流不再依赖浏览器暴露真实本地路径，文件输入统一通过上传控件进入后端托管项目工作区。

## 新行为

- 小说总结、文章总结、自定义总结和章节分割都使用上传文件控件选择 `.txt` 文件。
- 上传文件会保存到 `<runtime_base>/workspace/projects/<project_slug>/inputs/`。
- 生成文件默认写入 `<runtime_base>/exports/<project_slug>/<workflow>/`。
- 需要恢复未完成任务时，通过历史项目选择控件恢复项目名、上传文件列表、输出目录和最近任务状态。
- 自定义输出目录只通过浏览按钮或手动输入设置，后端打开目录接口会校验该路径。

## 仍然成立的浏览器限制

普通浏览器拖拽事件仍可能只提供 `File.name`，例如 `第1章-第10章.txt`，而不是完整文件系统路径。应用现在不再尝试从这个值推导本地目录，也不会把文件名拼接成伪绝对路径。

| 数据来源 | 可能值 | 当前处理 |
|---------|--------|----------|
| `File.name` | `第1章-第10章.txt` | 作为上传文件名使用 |
| `File.path` | 通常为 `undefined` | 不依赖 |
| `text/uri-list` | 通常为空或不可用 | 不依赖 |
| `text/plain` | 可能为空或只有文件名 | 不依赖 |

## 相关文件

- `frontend/src/hooks/useManagedProject.ts` — 上传、历史项目恢复和输出目录状态
- `frontend/src/components/forms/FormControls.tsx` — 上传文件、历史项目、输出目录控件
- `webui_backend/project_workspace.py` — 后端项目工作区、上传引用和导出目录
- `webui_backend/api_app.py` — 上传、历史项目、任务启动和打开目录接口
