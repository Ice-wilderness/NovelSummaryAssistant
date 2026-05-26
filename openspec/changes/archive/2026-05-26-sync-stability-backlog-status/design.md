## Context

稳定性审计报告保留了发现当时的风险描述；后续多个 change 已归档并解决了其中一部分风险。当前 `project_workspace.py` 拆分已经通过 `2026-05-26-split-project-workspace-services` 完成，但总览和 backlog 仍把它列为待拆分事项，README 的项目结构也还偏向拆分前的集中式描述。

本 change 是文档状态校准，不改变应用行为。实现时以归档 OpenSpec、当前文件布局和现有审计文档为依据。

## Goals / Non-Goals

**Goals:**

- 让稳定性审计总览和 backlog 清楚区分已完成的 `project_workspace.py` 拆分与仍未完成的 `TriggerScanPage.tsx`、`logic/utils.py` 拆分。
- 调整后续优先级，避免把已完成工作排在下一轮候选任务中。
- 更新 README 项目结构，使维护者能看到当前 `webui_backend/routes/` 与 `webui_backend/workspace_services/` 边界。
- 保留原始模块报告作为历史审计证据，不强行改写每个发现的原始语境。

**Non-Goals:**

- 不实施任何前端或后端重构。
- 不修改 OpenSpec 已归档 change 的内容。
- 不新增测试依赖，也不改变验证基线。
- 不重新审计整个项目。

## Decisions

1. 以总览和 backlog 作为当前状态来源。

   模块审计报告记录的是发现时状态，频繁回写所有模块报告会降低历史可追溯性。总览和 backlog 更适合作为“当前仍需处理什么”的入口，因此本次优先更新它们。

   备选方案是同步修改所有提到 `project_workspace.py` 的报告。这样会扩大文档 diff，也可能模糊原始审计证据，暂不采用。

2. README 只更新结构和维护者理解所需的入口描述。

   README 的目标是帮助用户和维护者理解当前项目布局。本次只校准过期结构，不加入完整维护者手册；测试命令、OpenSpec 流程和运行时规则可留给后续独立文档 change。

   备选方案是顺手补齐全部维护者文档。该范围会超出“状态校准”，容易和后续文档规划混在一起。

3. 用现有归档 change 和文件布局作为验证依据。

   文档变更的核心验证是确认 `openspec/changes/archive/2026-05-26-split-project-workspace-services/` 已完成，以及当前仓库存在 `webui_backend/workspace_services/`。不需要运行完整测试套件来验证文档措辞。

## Risks / Trade-offs

- 过度改写历史报告 -> 只更新当前状态入口，并在文档中说明原始报告保留发现时语境。
- 后续任务优先级仍会变化 -> 使用“建议优先级”措辞，避免把排序写成不可变承诺。
- README 信息再次过期 -> 让结构描述贴近目录边界，避免写入过多易漂移的实现细节。
