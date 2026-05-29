## Why

当前 WebUI 已覆盖核心功能，但整体仍偏传统三栏工具页，视觉层级、交互引导、动效反馈和工作流聚合感不足，难以匹配用户希望的现代化、舒适且高级的 PC 端工作台体验。

需要以“写作工作室”方向推进一次真实前端重构：demo 仅作为审美和信息架构参考，实际布局必须围绕小说总结、章节分割、雷点扫描、提示词、API 配置、项目修复、日志和进度等现有功能重新设计。

## What Changes

- 将现有 WebUI 重构为 PC 优先的“写作工作室”体验，重新组织主导航、项目上下文、当前任务、阶段进度、日志和主要操作区域。
- 保留并重新承载现有功能：小说总结、文章总结、自定义总结、章节分割、雷点扫描、提示词编辑、API 配置、项目历史、输出目录、修复建议、任务控制、实时日志。
- 引入更现代的视觉系统，包括更精致的排版、色彩、空间层级、焦点态、状态标签、卡片/面板节奏和可扫读的信息密度。
- 增加舒适且有克制的动效：页面入场、阶段流推进、面板切换、日志追加、状态变化、悬停/聚焦反馈、任务运行态提示。
- 改善交互逻辑和引导：让用户清楚当前处于哪个工作流、下一步该做什么、哪些配置会影响任务、任务运行后如何查看产物和处理异常。
- 允许新增前端库、扩展或插件来提升美观、动效和交互舒适度，只要不破坏现有功能、测试、构建和本地部署方式。
- 不把移动端适配作为目标；设计以 PC 桌面宽屏为主要使用场景，保留基本浏览器缩放/窄宽容错即可。

## Capabilities

### New Capabilities

- `studio-workbench-experience`: 定义 PC 优先的写作工作室信息架构、视觉品质、动效反馈、上下文引导和第三方前端增强能力。

### Modified Capabilities

- `webui-workbench`: 调整现有工作台的布局和交互要求，使核心功能在新工作室界面中仍可导航、可恢复、可控制、可查看日志和进度。

## Impact

- Affected code:
  - `frontend/src/App.tsx`
  - `frontend/src/components/layout/AppLayout.tsx`
  - `frontend/src/components/logs/LogPanel.tsx`
  - `frontend/src/components/StageProgressBar.tsx`
  - `frontend/src/components/forms/FormControls.tsx`
  - `frontend/src/views/*.tsx`
  - `frontend/src/views/trigger-scan/*.tsx`
  - `frontend/src/styles.css`
- Affected tests:
  - Layout, smoke, workflow page, trigger scan, form control, and task action tests may need updates for new structure and accessible labels.
- Dependencies:
  - Frontend dependencies may be added for animation, layout primitives, accessible controls, command surfaces, tooltips, stateful transitions, or polished UI components.
  - New libraries must remain compatible with Vite, React 18, TypeScript, Vitest, and the local WebUI deployment model.
- APIs:
  - No backend API changes are planned for the first implementation phase; the redesign should consume existing client APIs unless a later task identifies a necessary API gap.
- Documentation:
  - Existing style demos remain reference material only and must not be treated as exact implementation templates.
