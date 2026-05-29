# Studio WebUI 依赖选择

本文件记录 `modernize-studio-webui` 第一阶段新增前端依赖及其用途。原则是：允许引入库，但每个库都必须服务真实交互、动效或可访问性，不做纯炫技堆叠。

## 已选择依赖

| 依赖 | 用途 | 首批使用方向 |
| --- | --- | --- |
| `framer-motion` | React 动效库 | 页面/面板入场、日志追加、阶段流状态变化、hover/focus 反馈 |
| `@radix-ui/react-tooltip` | 可访问 tooltip 原语 | 图标按钮、状态徽标、复杂配置说明 |
| `@radix-ui/react-tabs` | 可访问 tabs 原语 | Studio inspector、雷点扫描视图、提示词/报告切换 |
| `@radix-ui/react-dialog` | 可访问弹窗原语 | 后续替换确认/上下文/修复说明类弹窗 |
| `@radix-ui/react-scroll-area` | 可访问滚动区域原语 | 日志、章节胶片、报告结果列表等高密度滚动内容 |

## 选择理由

- `framer-motion` 能减少手写动画状态管理，让运行态、阶段推进、日志追加等状态变化更自然。
- Radix primitives 不强制视觉风格，适合保留本项目自定义的写作工作室视觉，同时获得键盘、焦点和 ARIA 行为。
- 这些依赖都兼容 React 18、Vite、TypeScript 和本地 WebUI 部署方式。

## 使用约束

- 动效不得延迟错误、警告、确认和修复风险说明。
- Radix 组件只能替代交互原语，不能改变既有业务语义。
- 不一次性重写所有表单控件；先在 Studio shell、inspector、日志和关键页面中逐步采用。
- 新依赖引入后必须通过前端 typecheck/build 验证。
