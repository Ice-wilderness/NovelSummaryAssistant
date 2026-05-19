# 拖拽导入路径能力与限制

## 状态

完整路径可用时已支持自动修正；文件名-only 场景仍属于浏览器限制。

## 已支持的行为

- 目录输入框（小说目录、文章目录、章节分割输出目录）拖入完整文件路径时，前端会调用后端 `/api/utils/resolve-path`，由后端确认该路径是文件后返回文件所在目录。
- 文件输入框（章节分割源 TXT）拖入文件时保留文件路径，不会被误转成上级目录。
- 文件列表文本框拖入文件时会追加文件路径；后端会尽量把路径规范化为绝对路径。
- 临时调试日志已移除，生产控制台不再输出拖拽事件细节。

## 仍然存在的浏览器限制

当浏览器拖拽事件只能提供 `File.name`，例如 `第1章-第10章.txt`，而没有完整文件系统路径时，前端和后端都无法可靠推导该文件所在目录。

| 数据来源 | 可能值 | 说明 |
|---------|--------|------|
| `event.dataTransfer.getData("text/uri-list")` | `file:///C:/path/to/file.txt` 或空字符串 | 有完整 URI 时可解析；为空时不可用 |
| `event.dataTransfer.getData("text/plain")` | `C:\path\to\file.txt` 或空字符串 | 有完整路径时可解析；为空时不可用 |
| `File.path` | `C:\path\to\file.txt` 或 `undefined` | 普通浏览器通常不可用 |
| `File.webkitRelativePath` | 相对路径或空字符串 | 通常只在目录选择场景有效 |
| `File.name` | `第1章-第10章.txt` | 只有文件名，不能推导上级目录 |

因此，目录输入框收到纯文件名时只能按后端运行目录做兜底规范化，无法保证等同于文件真实所在目录；需要准确自动转父目录时，拖拽事件必须提供完整路径，或用户使用浏览按钮/粘贴完整路径。

## 相关文件

- `frontend/src/components/forms/FormControls.tsx` — 拖拽路径提取、目录/文件输入框区分和前端兜底提示
- `webui_backend/api_app.py` — `/api/utils/resolve-path` 路径解析接口
- `tests/test_api_app.py` — 路径解析接口回归测试
