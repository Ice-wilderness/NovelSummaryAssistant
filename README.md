# NovelSummaryAssistant

本项目正在从旧 CustomTkinter 桌面界面迁移到本地 WebUI。当前主入口为 FastAPI + React/Vite/TypeScript 工作台。

## 署名

- 原作者：`zhoufei_1314`
- 现作者：`Ice_wilderness`

## 启动 WebUI

### 构建模式

```powershell
cd frontend
npm install
npm run build
cd ..
python run_gui.py
```

默认地址为 `http://127.0.0.1:8000`。`run_gui.py` 会启动 FastAPI 后端，并在 `frontend/dist` 存在时托管前端页面。

### 开发模式

```powershell
python run_gui.py --no-browser
```

另开终端：

```powershell
cd frontend
npm install
npm run dev
```

开发模式下前端地址为 `http://127.0.0.1:5173`，Vite 会把 `/api` 请求代理到 `http://127.0.0.1:8000`。

### 端口参数

```powershell
python run_gui.py --host 127.0.0.1 --port 8010
```

## 配置和缓存

- API 配置：`api_configs.json`
- 提示词缓存：`prompt_cache/`
- 任务状态和断点缓存：`.summarizer_cache/`
- 旧窗口配置：`config.yaml`

这些本地文件默认不应提交到代码仓库。

## API Key 策略

API Key 支持两种来源：

- 本地配置文件中的 `key`
- 配置项中的 `key_env_var` 指向的环境变量

运行时优先使用环境变量；环境变量不存在时回退到本地配置文件中的 key。普通配置读取接口和 WebUI 默认只显示遮蔽后的 key，保存遮蔽值时会保留已有真实 key，避免误覆盖。

## 过渡入口

旧 CustomTkinter GUI 仍保留为过渡备用入口：

```powershell
python run_gui.py --legacy-gui
```

WebUI 冒烟测试和端到端验证完成后，再移除旧 GUI 代码和 `customtkinter` 依赖。

## 已知限制

- 浏览器无法直接读取任意本地绝对路径，当前 WebUI 的路径字段以手动输入或粘贴为主。
- 总结任务仍依赖本地 API 配置和可用的大模型服务。
- 旧 GUI 删除尚未执行，避免 WebUI 验证完成前失去备用入口。
