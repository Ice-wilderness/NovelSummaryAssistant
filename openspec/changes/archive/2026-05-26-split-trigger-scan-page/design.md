## Context

`frontend/src/views/TriggerScanPage.tsx` 当前约 89 KB，包含雷点档案 CRUD、规则组编辑、扫描项目选择、扫描配置、任务启动与控制、报告历史、报告详情、finding 过滤分页、finding 复核、上下文弹窗、剧透级别和多个 display helper。稳定性审计已将它列为当前前端最高维护风险之一。

本 change 是无行为变化重构。后端雷点扫描 API、数据模型、任务状态、报告格式和现有 WebUI 使用路径必须保持稳定。用户已允许为本次拆分引入前端测试依赖，因此实现可以在 `frontend/package.json` / `package-lock.json` 中增加最小测试工具链。

## Goals / Non-Goals

**Goals:**

- 把 `TriggerScanPage.tsx` 拆成职责清晰的组件、hooks 和纯工具模块。
- 保持现有雷点扫描页面行为、字段、默认值、标签页、API 调用和展示语义不变。
- 为拆出的高价值纯逻辑和轻量组件建立前端测试基础，降低后续重构风险。
- 让最终页面文件主要承担数据编排、tab 选择和跨区域状态连接，而不是承载全部 UI 和业务 helper。
- 按功能块提交，每个拆分边界运行对应验证。

**Non-Goals:**

- 不重新设计雷点扫描 UI。
- 不修改雷点扫描后端 API、报告 schema、任务 runtime 或持久化数据。
- 不引入全局状态库、路由库或第三方 UI 框架。
- 不顺手修复文章总结 partial success、上传内存风险或章节分割问题。
- 不实现 LLM 聚合功能。

## Decisions

1. 先抽纯 helper，再抽 UI 组件。

   `statusText`、`reportStatusText`、warning 文案、finding display、filter/pagination、profile draft clone/create 等逻辑适合先放入纯工具模块并补单元测试。它们不依赖 React 生命周期，迁移风险低，可以为后续组件拆分提供稳定基础。

   备选方案是先把 JSX 大块剪到组件文件。这样能快速缩短主文件，但如果 helper 和状态仍耦合在页面里，后续测试和复用收益有限。

2. 使用领域目录聚合雷点扫描前端模块。

   建议新增 `frontend/src/views/trigger-scan/` 或 `frontend/src/components/trigger-scan/`，按 `profile`、`scan-config`、`results`、`finding-review`、`context-modal`、`utils` 等职责组织。具体路径以实现时最小 diff 和现有导入风格为准，但不把通用性不足的组件提升到全局 `components/common`。

   备选方案是把所有拆出组件平铺在 `components/`。该方式会稀释通用组件目录的含义，暂不采用。

3. 使用 Vitest + Testing Library 建立最小测试基础。

   该项目使用 Vite + React，Vitest 与现有构建工具链匹配。Testing Library 可覆盖拆出的轻量组件交互。优先新增 `npm run test` 或 `npm run test:run` 脚本，并把测试范围控制在本 change 拆出的模块，不一次性建设完整前端测试体系。

   备选方案是只用 `npm run build`。这无法捕捉 filter、warning、review action 等行为漂移；用户已允许新增依赖，因此采用更可靠的最小测试基础。

4. 保持页面级状态迁移渐进。

   初期可以让 `TriggerScanPage` 继续持有跨区域状态，把拆出的组件做成受控组件；当某个状态域边界稳定后，再抽 `useTriggerProfiles`、`useTriggerScanConfig`、`useTriggerReports` 等 hooks。这样可以避免一次性移动所有 `useState/useEffect` 带来的回归风险。

   备选方案是直接把所有状态拆进多个 hooks。它会让跨 tab 的刷新、任务事件和 report polling 更难一次性验证。

## Risks / Trade-offs

- 行为漂移 -> 以现有 `webui-workbench` / `trigger-scan-workflow` 规格为行为边界，拆分后运行 `npm run build` 和新增前端测试。
- 组件 props 过宽 -> 先接受少量受控组件 props，后续在边界稳定后再抽 hooks，避免提前设计过度抽象。
- 测试依赖带来 lockfile churn -> 只添加必要测试依赖，并使用现有 npm / `package-lock.json` 约定。
- 样式或布局回归 -> 复用现有 className 和 CSS，不在本 change 中重做视觉设计。
- 拆分过细导致导航成本上升 -> 每个文件对应真实页面区域或纯逻辑边界，不为单个 JSX 小片段创建文件。

## Migration Plan

1. 添加前端测试脚本和最小测试配置，先验证现有 `npm run build` 仍通过。
2. 抽出纯 display/profile/filter helper，并补单元测试。
3. 拆出 profile 管理 tab 的组件边界，保持受控 props 和现有 API 调用语义。
4. 拆出 scan config / startup checks 区域，保持字段默认值和请求 payload 不变。
5. 拆出 report history/detail、finding list、review action 和 context modal 区域，保持 warning、剧透级别、分页过滤和复核行为不变。
6. 清理 `TriggerScanPage.tsx` 中本次拆分产生的未使用 import/helper，运行 `npm run test` 和 `npm run build`。

回退策略是按拆分提交逐个 revert。由于不改变后端契约或持久化数据，不需要运行时迁移。

## Open Questions

- 测试脚本名称默认使用 `test` 或 `test:run`，实现时以不干扰现有 `build/typecheck/dev` 为准。
- 组件目录最终选择 `views/trigger-scan` 还是 `components/trigger-scan`，实现时根据拆出组件是否仅服务该页面决定。
