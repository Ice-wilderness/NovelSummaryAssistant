# 拖拽导入无法获取完整路径的问题

## 状态

已知限制，待解决。

## 现象

用户在小说总结页面将 `.txt` 文件拖入"小说目录"输入框时，只能获取到文件名（如 `第1章-第10章.txt`），无法获取完整的文件系统路径（如 `C:\Users\xxx\novel\第1章-第10章.txt`）。因此也无法将文件路径自动转换为所在目录。

## 根因

这是**浏览器安全沙箱的硬性限制**。当用户从操作系统文件管理器拖拽文件到浏览器时：

| 数据来源 | 预期值 | 实际值 |
|---------|--------|--------|
| `event.dataTransfer.getData("text/uri-list")` | `file:///C:/path/to/file.txt` | **空字符串** |
| `event.dataTransfer.getData("text/plain")` | `C:\path\to\file.txt` | **空字符串** |
| `File.path` | `C:\path\to\file.txt` | **undefined**（Electron 专有属性） |
| `File.webkitRelativePath` | 相对路径 | **空字符串**（仅 `<input webkitdirectory>` 场景有效） |
| `File.name` | `第1章-第10章.txt` | ✅ 唯一的可用数据 |

经实际调试确认（2026-05-19），用户环境中拖拽事件的所有 MIME 类型数据均为空，只有 `File.name` 提供了文件名。

## 当前代码处理

`frontend/src/components/forms/FormControls.tsx` 中的 `getDroppedPaths()`：

1. 优先从 `text/uri-list` 提取路径（完整路径，当前环境为空）
2. 其次从 `text/plain` 提取路径（当前环境为空）
3. 以上皆空时，回退到 `File.path → File.webkitRelativePath → File.name`
4. 最终落入 `File.name`，只有纯文件名

`handleDrop` 中的目录提取逻辑（`extractParentDir` 内联代码）依赖路径中包含目录分隔符（`/` 或 `\`），纯文件名无法提取父目录。

## 可行方案

### 方案 A：后端搜索最近目录（推荐）

**思路**：
- 后端维护一个 `recent_dirs.json`，记录用户通过"浏览"按钮选择过的目录
- 当拖入文件名时，前端调用后端搜索接口
- 后端在最近目录和 CWD 中搜索匹配的文件名
- 找到后返回完整路径，前端自动提取父目录

**优点**：对用户透明，利用已有的浏览操作建立搜索范围
**缺点**：首次使用或更换目录时需要先浏览一次；搜索范围有限

### 方案 B：使用原生辅助进程

**思路**：
- 运行一个轻量 Python 脚本，通过 WebSocket 与前端通信
- 前端拖入文件时发送文件名
- Python 脚本通过 `ctypes` / `win32api` 查询操作系统最近访问的文件
- 返回匹配的完整路径

**优点**：可以获取系统级文件信息
**缺点**：需要额外进程；跨平台兼容性问题；实现复杂

### 方案 C：接受限制，优化浏览按钮体验

**思路**：
- 明确告知用户拖拽无法获取完整路径
- 将"浏览"按钮做得更显眼
- 添加"最近使用目录"快捷选择下拉框
- 支持粘贴路径（Ctrl+V）

**优点**：实现简单，不影响稳定性
**缺点**：拖拽体验仍然受限

## 调试日志

代码中已临时添加 `console.log` 调试日志（`[getDroppedPaths]` 和 `[PathInput drop]`），用于后续排查。实现方案后应移除或降级为 `debug` 级别。

## 相关文件

- `frontend/src/components/forms/FormControls.tsx` — 拖拽路径提取与处理
- `webui_backend/api_app.py` — `/api/utils/resolve-path` 路径解析接口
- `webui_backend/config_service.py` — 可添加最近目录管理（尚未实现）
