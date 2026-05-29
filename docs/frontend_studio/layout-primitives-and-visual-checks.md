# Studio 布局原语与视觉验证

本说明记录 `modernize-studio-webui` 落地后的前端维护约定，方便后续页面继续沿用 Studio 工作台体验。

## 布局与展示原语

- `frontend/src/components/studio/StudioPrimitives.tsx`
  - `StudioPanel`：通用信息面板，用于 inspector、上下文索引和可独立阅读的工作区块。
  - `StudioCard`：轻量状态卡，适合统计、提示和重复小项。
  - `StudioStatusBadge`：带圆点的状态标签，统一表达 idle/running/success/warning/danger 等状态。
  - `StudioButton`、`StudioTooltip`、`StudioTabs`、`StudioScrollArea`：基于项目样式和 Radix 原语的交互基础件。
  - `StudioMotionSurface`：页面/面板入场动效容器，适合页面迁移时包裹新的 Studio 区块。
- `frontend/src/components/studio/StudioStageFlow.tsx`
  - 从任务事件或任务生命周期生成顶部阶段流，保留 pending/running/paused/cancelled/success/partial/failed/interrupted 语义。
- `frontend/src/components/studio/taskPresentation.ts`
  - 集中维护任务状态文案、状态 tone、任务类型名和终态提示。
- `frontend/src/studio.css`
  - 承载 Studio shell、页面级 Studio 布局、状态动效和 PC 工作台视觉系统。
- `frontend/src/styles.css`
  - 继续保留表单、日志、表格、上传、提示词、雷点扫描等共享业务控件样式；旧三栏工作台壳样式已清理。

## 依赖用途

- `framer-motion`：用于页面入场、阶段流推进、日志追加和面板状态变化。
- `@radix-ui/react-tabs`、`@radix-ui/react-tooltip`、`@radix-ui/react-scroll-area`、`@radix-ui/react-dialog`：提供可访问交互原语，不绑定视觉风格。
- `lucide-react`：统一图标按钮和区块标题图标。

新增依赖或新原语时，应优先服务真实状态反馈、键盘/焦点行为、长任务可读性或维护成本，不为纯装饰引入同类重复库。

## PC 桌面视觉检查

先启动 WebUI：

```bash
npm run dev
```

然后运行：

```bash
npm run check:desktop
```

脚本会使用本机 Chrome/Edge 的 headless 模式在 `1440x1000` 视口下截图，默认覆盖：

- `empty`：空项目入口。
- `loaded`：已加载项目上下文。
- `running`：运行中任务和阶段流。
- `terminal`：终态任务和可用结果。
- `repair`：修复/警告状态。
- `trigger`：雷点扫描报告复核入口。
- `logs`：日志密集会话。

截图输出到 `.codex_tmp/studio-desktop-checks/*.png`，同时保留第一张到 `.codex_tmp/studio-desktop-check.png` 作为兼容入口。

可用环境变量：

- `STUDIO_CHECK_URL`：默认 `http://127.0.0.1:5173`。
- `STUDIO_CHECK_VIEWPORT`：默认 `1440,1000`。
- `STUDIO_CHECK_SCENARIOS`：逗号分隔，例如 `running,logs`。
- `STUDIO_CHECK_BROWSER`：指定 Chrome/Edge 可执行文件。
- `STUDIO_CHECK_OUTPUT_DIR`：多场景截图目录。
- `STUDIO_CHECK_OUTPUT`：兼容单张截图路径。

视觉检查 fixture 只在 Vite 开发模式下通过 `studioVisualFixture` URL 参数启用，并会跳过启动数据请求，避免本地后端不可用干扰截图。生产构建不会启用该 fixture。
