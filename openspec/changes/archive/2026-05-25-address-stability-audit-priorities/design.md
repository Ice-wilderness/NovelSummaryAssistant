## Context

稳定性审计覆盖了前端工作台、WebUI 后端、总结工作流、雷点扫描、章节分割、项目工作区和测试质量。现有基线是 `python -m pytest` 和 `npm run build` 均通过，但审计发现若干问题会直接影响用户对长任务结果的判断：取消可能显示为失败，雷点扫描暂停不会真正阻塞，续扫进度可能回退或超过总量，部分失败报告可能显示为完成，aggregation prompt 暴露给用户却没有参与 LLM 调用。

本次变更优先处理会改变用户可见状态或数据安全边界的问题。大型文件拆分、前端组件化和后端路由拆分仅作为受测试保护的后续维护任务，不在本次一次性完成。

## Goals / Non-Goals

**Goals:**

- 所有支持取消的长任务在用户取消后统一进入 `cancelled` 终态。
- 雷点扫描暂停必须阻塞后续扫描/验证 API 调用，恢复后继续执行。
- 雷点扫描续扫使用同一进度口径：`selected_total` 作为总数，`completed_from_resume + processed_current_run` 作为完成数。
- 雷点扫描报告只在选中章节全部扫描且后续阶段成功时标记 `completed`；部分章节未扫描完成时标记 `partial_failed`。
- 续扫验证只复验未验证或验证状态不明的历史 finding，新 finding 按当前配置正常验证；无法获得上下文时保留结果并输出 warning。
- 本次保留 deterministic 聚合，并同步提示词编辑器和规格说明，避免用户误以为 aggregation prompt 会触发 LLM 调用。
- 保留 API 失败诊断日志的完整输入输出以便排查，同时继续脱敏密钥，并增加清理/保留策略入口。
- 删除项目时只删除可证明由系统管理的输出目录，保留自定义或归属不明目录。

**Non-Goals:**

- 不在本次引入 LLM aggregation prompt 调用；该 B 方案记录为后续独立 change。
- 不重构整个 `api_app.py`、`TriggerScanPage.tsx` 或 `logic/utils.py`。
- 不改变现有 LLM 提示词内容本身，除非是为了标注 aggregation prompt 的运行时状态。
- 不默认截断 API 失败日志中的完整输入输出。

## Decisions

### 1. 取消统一由 TaskRuntime 收敛

业务 runner 不再把 `asyncio.CancelledError` 转成 `False`、普通文本或 `failed` 结果，而是允许其传播到 `TaskRuntime`。`TaskRuntime` 负责记录 cancelled 终态、发出 terminal 事件，并让项目历史保存同一语义。

替代方案是每个 runner 自己写取消状态转换。该方案会保留当前漂移风险，因此不采用。

### 2. 雷点扫描暂停复用共享暂停检查

精确扫描和验证阶段不得继续使用 `pause_signal.wait(0)` 这种立即返回的调用。实现应复用现有 async pause 检查，或提供等价的 awaitable pause gate，确保暂停期间不会发起下一次 LLM API 请求。

替代方案是在前端只禁用按钮或只暂停进度展示。该方案无法停止后端 API 调用，因此不采用。

### 3. 续扫进度使用选中范围总量

雷点扫描启动时计算：

- `selected_total`: 本次用户选中章节总数。
- `completed_from_resume`: 兼容 scan state 且已完成扫描的章节数。
- `pending_total`: 本轮仍需扫描的章节数。
- `processed_current_run`: 本轮已扫描章节数。

前端 stage progress 中展示 `completed_from_resume + processed_current_run` / `selected_total`。worker 不得用本轮计数覆盖累计计数。

### 4. 续扫验证按 finding 验证状态分流

历史 finding 已明确通过验证或被标记为用户复核结果时，不重复提交给验证 LLM。历史 finding 未验证、验证状态缺失或来自旧报告时，后端尝试重建其章节 paragraph index 后再验证。若章节文件或 paragraph index 无法恢复，报告保留该 finding，并加入 `unverified` warning，避免静默丢失或误删。

### 5. 报告状态区分完整成功和部分失败

`completed` 只表示选中章节全部完成扫描，且验证、聚合、报告写入未发生阻断性错误。非取消异常导致仍有选中章节未扫描时，报告状态为 `partial_failed`，并记录未扫描章节、失败阶段、可用 finding/event 数量和 warning。用户取消产生 `cancelled` 任务状态，已产出的部分报告可以保留，但不能标为 `completed`。

### 6. 聚合保持 deterministic，LLM 聚合作为后续计划

本次不引入额外聚合 LLM 调用。后端可以继续渲染或保留 aggregation prompt 配置用于兼容旧配置，但运行时、提示词编辑器和文档必须明确：当前事件聚合由本地规则完成，aggregation prompt 不影响结果。

后续 B 方案应单独设计：调用 aggregation prompt、解析 ScanEvent、失败 fallback、成本提示和测试矩阵。

### 7. API 失败日志保留完整输入输出

为了排查模型与提示词问题，失败诊断文件继续保留完整输入消息、输入文本、响应文本和错误上下文。实现只继续脱敏 API key、authorization header 等密钥字段。容量治理通过清理入口、保留数量/天数配置或维护命令解决，不通过默认截断解决。

### 8. 输出目录删除依赖 ownership metadata

系统创建的 managed export directory 写入 ownership metadata，记录 project slug、创建者标识和目录用途。删除项目时，只有目录位于 managed export root 且 metadata 匹配当前项目时才递归删除。自定义目录、导入目录、metadata 缺失或不匹配的目录一律保留，并向前端返回 preserved 信息。

### 9. 每个小功能完成后提交 Git checkpoint

实施本变更时，每完成一个可独立验证的小功能或任务子集，先运行该小功能对应的最小验证命令，再创建一个聚焦的 git commit。commit 只包含该小功能直接相关的代码、测试和文档变更，不混入后续任务或无关重构。

## Risks / Trade-offs

- 旧任务或旧报告缺少验证状态 → 通过兼容读取和 `unverified` warning 处理，不静默升级为 verified。
- `partial_failed` 是新增用户可见状态 → 前端和报告历史必须同步支持，否则会显示未知状态。
- 保留完整诊断日志仍有隐私和磁盘风险 → 继续脱敏密钥，并提供清理/保留策略；README 或维护文档需说明风险。
- ownership metadata 只能保护新创建或迁移后目录 → 旧目录缺少 metadata 时默认保留，牺牲自动清理换取不误删。
- 不做 LLM 聚合会限制跨章节语义聚合质量 → 在本 change 的任务中保留后续计划，避免遗忘。
- 高频提交会增加 apply 阶段的 git 操作成本 → 以“可独立验证的小功能”为边界提交，保持 commit 小而完整。

## Migration Plan

1. 为新生成的 managed export directory 写入 ownership metadata；旧 managed 目录可在下次保存/任务启动时补写，无法确认归属时保持不删除。
2. 读取旧 trigger scan report 时兼容没有 `partial_failed`、`warnings` 或 finding verification metadata 的结构。
3. 更新前端状态映射，兼容旧状态，同时显示新增的 `cancelled`、`partial_failed` 和 `unverified` warning。
4. 更新 OpenSpec 和提示词编辑器说明，明确 aggregation prompt 当前不参与 LLM 调用。
5. 验证顺序优先跑新增定向测试，再跑 `python -m pytest` 和 `npm run build`。

## Open Questions

- LLM aggregation prompt 的 B 方案暂不进入本次实现；后续 change 需要单独确认成本、失败 fallback 和 UI 提示。
