# 配置、文件上传与工作区审计

## 模块职责

该模块覆盖 API 配置、用户设置、提示词缓存、项目工作区、上传文件、导出目录、运行时缓存、报告输出和本地路径能力。

## 关键入口

- `api_configs.json`
- `user_settings.json`
- `chapter_patterns.json`
- `prompt_cache/`
- `workspace/`
- `exports/`
- `webui_backend/config_service.py`
- `webui_backend/project_workspace.py`
- `webui_backend/workspace_services/`
- `webui_backend/file_services.py`
- `logic/utils.py`（兼容门面）
- `logic/api_logging.py`
- `logic/prompt_runtime.py`

## 发现

### 已治理：项目删除依赖目录名判断，缺少 ownership 标记

- 现象：删除项目时会删除 workspace project dir，并在 export dir 存在且目录名等于 project_slug 时删除 export dir。
- 证据：`ProjectWorkspaceService.delete_project` 使用 `if export_dir.exists() and export_dir.name == project_slug: shutil.rmtree(export_dir)`。
- 影响：如果用户把自定义输出目录设置为某个刚好以 project_slug 命名的重要目录，删除项目可能误删用户数据。
- 原始风险级别：高。
- 当前状态：系统创建的导出目录会写入 ownership metadata；删除项目时只删除 ownership 与当前项目匹配的输出目录，缺失或不匹配时保留并向 WebUI 返回原因。
- 后续建议：继续保持自定义目录不递归删除的边界，避免用目录名作为删除依据。

### 已治理：自定义输出目录失败时静默回退

- 现象：`resolve_output_selection` 对不存在、不可用或不是目录的 custom path 多数情况下返回 default dir 和空 custom。
- 证据：`project_workspace.py` 中 `except OSError: return default_dir, ""`，路径是文件时也回退。
- 影响：用户以为输出到了自定义目录，实际写到默认目录；前端状态和后端落盘可能产生困惑。
- 原始风险级别：中。
- 当前状态：保存项目、任务启动前 auto-save、输出迁移和 workflow task 创建均使用 strict 验证；无效项目级自定义输出目录会返回明确错误，并保留前一次已保存输出目标。历史项目、导入项目和项目详情读取使用 compat 语义，旧路径不可用时回退当前默认输出目录并返回 warning。
- 后续建议：继续保持“主动操作不静默回退、历史读取兼容回退”的边界，避免输出目标被系统替用户改写。

### 已部分治理：运行时失败日志可能无上限增长

- 现象：API 失败诊断日志写入 `.summarizer_cache/api_failures/`，没有数量、大小或过期清理。
- 证据：`logic/api_logging.py` 每次 fail 写独立 JSON 文件，`logic/llm_api.py` 写入输入和响应字段。
- 影响：长篇任务和重试失败会快速占用磁盘，并保留大量用户内容。
- 原始风险级别：中。
- 当前状态：失败诊断已补敏感凭据脱敏、清理/保留路径和对应测试；非密钥输入/输出仍会作为本地诊断资料保留。
- 后续建议：如需进一步降低隐私/容量风险，再增加诊断开关、字段截断和 UI 可见清理入口。

### 已治理：路径能力横跨浏览器上传和本地选择器

- 现象：项目一方面强调上传工作流，另一方面仍保留 `/api/browse/file`、`/api/browse/directory` 和 `open_directory`。
- 证据：`api_app.py` 暴露 browse/open-directory，`local_picker.py` 使用 tkinter，`project_workspace.py` 调用 OS open。
- 影响：在 headless、无 tkinter、打包环境或远程运行时容易失败；安全边界也更难解释。
- 原始风险级别：中。
- 当前状态：项目定位已按本地单用户应用处理。文件/目录选择器和打开输出目录失败时会转换为可操作错误，前端显示在触发控件附近；`open_directory` 后端从项目 metadata 派生当前有效输出目录，并拒绝非当前项目输出目录 path。
- 后续建议：继续避免把 `open_directory` 扩展成通用本地路径打开能力；frozen 打包环境仍建议做人工冒烟验证。

### 已治理：配置损坏时默认恢复但缺少用户提示

- 现象：`load_api_configs`、`load_user_settings` 在 JSON 损坏时返回默认值。
- 证据：`config_service.py` 捕获 JSONDecodeError/OSError 后返回默认配置。
- 影响：配置文件损坏会表现为配置丢失。
- 原始风险级别：低到中。
- 当前状态：API 配置、用户设置和章节模式配置损坏时，后端会尝试复制原文件到同级 `.bak` 或非覆盖 `.bak.N`，再返回安全默认值；备份路径或备份失败原因会作为配置域 warning 返回，WebUI 在对应设置页或章节模式控件局部展示。
- 后续建议：当前不做配置 diff、恢复历史管理或自动合并损坏配置；如后续需要更强恢复能力，应单独设计。

## 优化空间

- 保持系统管理输出目录的 ownership/managed 标记，并避免对自定义目录做递归删除。
- 前端已在读取文件前执行 100 MB 上传大小预检；后端上传限制仍是最终校验边界，长期如需支持更大文件可另行设计 multipart/stream 上传。
- 维持配置损坏恢复的统一备份策略，并在新增配置域时复用配置域 warning 结构。
- 为诊断日志增加用户可见清理动作和更细的披露文案。

## 验证

- `.gitignore` 已排除本地密钥、workspace、exports、prompt_cache、chapter_patterns 和构建产物。
- `python -m pytest` 通过，包含 config service、file service、project workspace、API route 和 workflow 相关测试。
- `test_config_service.py` 覆盖 API config、user settings、chapter patterns 损坏备份/warning 和备份失败。
- `test_project_workspace.py` 覆盖输出目录 ownership metadata、ownership mismatch 保留、缺失 ownership 保留说明、strict 自定义输出目录拒绝和 compat 历史读取 warning。
- `test_api_app.py` 覆盖任务启动/项目保存拒绝无效自定义输出目录、显式默认目录回退、`open_directory` 输出目录边界和本地能力错误归一化。
