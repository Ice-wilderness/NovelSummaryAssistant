## Context

当前项目状态来自多处：项目 metadata、`StateManager` 进度 JSON、持久化 task summary、章节/分段中间产物、最终总结文件、雷点扫描报告和导入目录中的历史文件。前几轮治理已经让终态任务摘要可持久化，也让 `interrupted` 与 `partial_failed` 在前后端可见；剩余问题是这些状态来源可能互相矛盾。

典型矛盾包括：状态记录显示最终总结已完成但最终文件被手工删除；用户切换 Markdown/TXT 输出格式后旧格式文件仍在；导入旧项目时有输出文件但缺少新 metadata；中间章节总结缺失但项目历史仍显示成功。用户要求本 change 做完整闭环，因此本设计包含异常完成识别、repair plan、用户确认后的修复/续跑任务，但不做静默自动重建。

## Goals / Non-Goals

**Goals:**

- 在项目历史、项目详情和导入项目时统一执行状态/输出 reconcile。
- 区分正常完成、普通未完成、异常完成、状态 metadata 不完整和不可修复。
- 生成可测试、可展示的 repair plan，明确每个动作是仅校正 metadata/index/path，还是需要 LLM 补齐总结内容，以及是否可能覆盖文件、是否可能产生与原结果不同的新输出。
- 支持用户显式触发修复任务，优先校正状态/索引/路径；需要补齐总结内容时，只重跑可安全识别的缺失阶段并要求 LLM/内容变化确认。
- 保留原始任务历史，不把异常完成误改写成失败或未完成。
- 兼容旧项目、旧 task summary 和旧导入目录。

**Non-Goals:**

- 不实现完整 task event history、`Last-Event-ID` 回放、SSE heartbeat 或后端重启后自动恢复 running task。
- 不在项目加载、历史列表或导入过程中自动调用 LLM。
- 不保证重新生成结果与原始 LLM 输出完全一致。
- 不为所有工作流一次性实现同等深度修复；本轮优先覆盖小说总结相关输出，其他工作流可先返回 unsupported 或 blocked repair plan。
- 不删除或清理用户手工移动到输出目录中的未知文件。

## Decisions

### 1. 使用项目级 reconciliation status，而不是新增任务 lifecycle

新增项目层字段，例如 `reconciliation_status`、`reconciliation_warnings`、`output_checks` 和 `repair_plan`。推荐状态值：

- `ok`: 状态记录和关键输出一致。
- `incomplete`: 没有可靠完成记录，也没有对应完成产物。
- `abnormal_completed`: 曾记录完成或部分完成，但当前关键产物缺失、不可读或与保存格式不一致。
- `state_incomplete`: 产物存在，但状态 metadata 或 task summary 不完整，无法证明普通完成。
- `unsupported`: 当前 workflow 暂不支持完整 reconcile 或 repair。

理由：任务 lifecycle 已经承载 `pending/running/success/failed/cancelled/partial_failed/interrupted` 等运行时状态。把“输出文件后来丢失”塞进任务状态，会改写历史事实，也会污染任务控制逻辑。项目级 reconcile 可以同时保留“上次任务成功”和“当前输出异常”。

替代方案：新增任务状态 `abnormal_completed`。缺点是需要改动 task runtime、SSE、前端控制状态和历史标签，并且语义上它不是任务执行终态。

### 2. Reconcile 只读、幂等、可降级

Reconcile 过程只读取 metadata、task summary、进度 JSON 和文件系统，不写入输出、不修复文件、不调用 LLM。它可以在历史列表中轻量执行，在项目详情/导入时执行更完整检查。

推荐分层：

- 历史列表：返回 summary 级别状态、主要 warning、是否有 repair plan 摘要。
- 项目详情/导入：返回完整 `output_checks` 和 `repair_plan`。
- 修复任务结束后：重新执行完整 reconcile，并持久化必要的项目 metadata 更新时间和最新 task summary。

替代方案：历史列表中做完整扫描。优点是状态最准确；缺点是项目多时会拖慢页面加载，也可能因单个损坏项目影响列表体验。

### 3. Repair plan 是后端生成的执行合同

Repair plan 不只是 UI 文案，应包含稳定的 action id 和机器可读字段：

- `action_id`
- `label` / `description`
- `status`: `available` 或 `blocked`
- `blocked_reason`
- `required_inputs`
- `affected_outputs`
- `repair_kind`: 例如 `metadata_reconcile`、`index_rebuild`、`path_rebind`、`summary_content_regeneration`
- `requires_llm`
- `may_overwrite`
- `may_change_content`
- `estimated_scope`: 例如 `final_output_only`、`missing_intermediates`、`full_rerun`

UI 只展示和提交后端返回的 action id，不自行推断修复方式。启动修复时后端必须重新计算或校验 plan，防止用户打开页面后文件状态又变化。

替代方案：前端根据 warnings 组合修复按钮。缺点是会把文件/工作流语义分散到前端，后续新增输出格式或工作流时容易漂移。

### 4. 修复任务必须显式确认成本和覆盖风险

修复动作分三类：

- `metadata_or_index_repair`: 仅校正项目 metadata、进度摘要、历史索引、输出路径绑定或导入目录中的缓存位置，不生成新的总结正文，不调用 LLM。
- `summary_content_regeneration`: 补齐小总结、大总结、超级总结、终极总结、文章总结或自定义总结正文。对本项目而言，这类修复 SHALL 视为需要 LLM，因为总结正文不是简单拼接或格式转换。
- `rerun_missing_stage`: 只重跑缺失章节/分段/最终阶段。需要源文件、章节文件、设置和 API 配置，并 SHALL 标记为需要 LLM 与内容变化确认。
- `blocked`: 缺少源文件、章节文件、配置或 workflow 尚未支持时，只显示原因。

任何 `requires_llm`、`may_overwrite` 或 `may_change_content` 的 action 都要求前端传递确认标记，后端缺少确认时返回 validation error。无 LLM repair 不得生成或改写总结正文；它只能更新状态、索引、路径绑定或类似的派生 metadata。

替代方案：点击修复后直接开始最合理动作。缺点是会静默产生 API 费用，且重新生成内容可能与原结果不一致。

### 5. 先聚焦小说总结输出，保留统一模型

第一轮实现建议优先覆盖小说总结项目，因为它的状态/输出 reconcile 风险最高，且已有章节文件、中间总结、最终输出和项目历史的复杂组合。小说总结的内容补齐动作统一按 LLM 修复处理；不调用 LLM 的动作只覆盖 metadata/index/path 校正。文章总结、自定义总结、章节分割和雷点扫描可先使用同一 response model 返回 `unsupported` 或有限 repair plan，再按测试风险逐步补齐。

替代方案：一次性覆盖所有工作流。缺点是容易把任务范围扩大到不可控，尤其是雷点扫描报告、验证状态和 summary 类 partial result 的修复语义并不完全相同。

### 6. 输出检查由工作流 adapter 提供

建议在 `webui_backend/workspace_services/` 下新增 focused module，例如 `reconciliation.py`，并定义轻量 adapter：

- 读取项目 metadata、任务摘要和低层进度状态。
- 按 workflow 生成 expected outputs。
- 生成 `OutputCheck` 列表和 repair actions。
- 不直接执行 LLM 或文件写入。

修复执行进入现有任务体系，可在 `workflow_services.py` 或新的 repair runner 中调用已有总结 workflow 的可复用阶段。`project_workspace.py` 继续作为门面，避免重新膨胀。

替代方案：把 reconcile 逻辑直接写在 API route 或页面加载路径。缺点是难以单测，也会逆转前几轮拆分收益。

## Risks / Trade-offs

- 重新生成内容可能与原始结果不同 -> 在 repair plan 和确认对话中明确 `may_change_content`，并把 repair task 作为新任务记录保存。
- 修复可能产生 LLM 费用 -> 所有总结正文补齐 action 都必须设置 `requires_llm` 并要求用户确认；后端缺少确认时拒绝启动。
- 历史列表 reconcile 过慢 -> 列表只做轻量检查，详情页和导入流程做完整检查。
- 旧项目 metadata 不完整 -> 返回 `state_incomplete` 或 blocked reason，不阻塞项目列表。
- 覆盖已有文件造成数据损失 -> 默认不覆盖；需要覆盖时 repair action 标记 `may_overwrite` 并要求显式确认。
- 所有 workflow 一次性完整修复范围过大 -> 首轮以小说总结为主，其他 workflow 先返回 unsupported/blocked，并用统一模型保留后续扩展位置。
- 状态名称增加导致前端文案混乱 -> 项目 reconcile 状态和任务 lifecycle 分开展示，测试覆盖历史标签、详情 warning 和修复入口。

## Migration Plan

1. 新增 response model 时保证字段可选；旧前端或旧 metadata 缺少 reconcile 字段时仍按现有状态展示。
2. 后端先在项目详情和导入路径接入完整 reconcile，再把轻量结果接入项目历史列表。
3. 前端先显示 warning 和 blocked/available repair plan，再接入 repair task start。
4. Repair task 以新任务记录写入，不修改旧 task summary；任务结束后刷新项目详情和历史。
5. 若实现过程中发现某个 workflow 的修复语义不清晰，先返回 unsupported repair plan，并在任务列表中保留后续扩展项。
