## Context

当前雷点扫描工作台有四个标签页：档案（规则配置）、扫描（配置和执行）、结果（报告查看）和跳读（清单管理）。跳读清单是一个独立于扫描报告的持久化列表，允许用户将扫描发现加入清单、手动添加条目、编辑备注和导出 Markdown。该功能通过以下组件实现：

- **数据模型**：`SkipListItem`（单个条目）和 `SkipList`（条目集合），均定义在 `trigger_models.py`
- **存储层**：`SkipListStore` 类（`reporting.py`），负责 JSON 文件的读写、CRUD 和 Markdown 导出
- **API 层**：6 个 REST 端点（`api_app.py`）覆盖清单的增删改查和导出
- **前端**：`TriggerScanPage.tsx` 中完整的标签页 UI，包括手动添加表单、按章节分组的条目表格、备注编辑和删除操作
- **进度展示**：`project_workspace.py` 中"跳读清单"作为一个进度阶段，显示条目数量

跳读建议（`skip_advice`）是 AI 扫描输出的一个字段，在详细剧透级别下展示，由 `generate_skip_advice` 配置开关控制。该功能与跳读清单独立——建议文本直接嵌入扫描报告中，不依赖清单存储。

## Goals / Non-Goals

**Goals:**
- 完全移除跳读清单功能：数据模型、存储逻辑、API 端点、前端 UI、进度展示
- 清理与跳读清单相关的规范文档
- 保持跳读建议（`skip_advice`）生成和展示功能不变

**Non-Goals:**
- 不移除 `generate_skip_advice` 配置开关
- 不移除 `skip_advice` 字段及其在 AI prompt 和结果展示中的使用
- 不修改扫描报告的 JSON 结构和文件格式
- 不修改已有的扫描历史记录文件（旧报告中的 `in_skip_list` 字段将被忽略但不会导致错误）

## Decisions

### 移除范围：清单功能 vs 跳读建议

**决定**：仅移除跳读清单（数据存储 + UI 管理），保留跳读建议（AI 生成 + 内联展示）。

**理由**：跳读建议是 AI 模型在扫描时生成的文本片段，直接嵌入扫描报告的 `spoiler_levels.detailed.skip_advice` 字段中，在结果表格的"详细"视图下展示。它无需独立存储和 CRUD 操作，代码量很小（前端仅一个 switch + 展示行）。而跳读清单是一个完整的 CRUD 功能模块，包含独立的 JSON 文件存储、6 个 API 端点、一个标签页 UI。两者虽然概念相关，但耦合度低，可以独立移除。

### 清理前端状态和函数

**决定**：移除 `TriggerScanPage.tsx` 中所有与跳读清单相关的状态（`skipList`、`skipDraft`）、函数（`loadSkipList`、`addFindingToSkipList`、`addManualSkipItem`、`updateSkipItem`、`deleteSkipItem`、`exportSkipList`、`updateSkipDraft`）、类型引用和 UI 渲染函数（`renderSkipTab`）。将 `TriggerTab` 类型从 `"profiles" | "scan" | "results" | "skip"` 改为 `"profiles" | "scan" | "results"`。

**理由**：直接移除是最简洁的方式。没有向后兼容的需求。

### API 端点移除

**决定**：移除以下 6 个端点及辅助函数 `skip_list_store_for_project`：
- `POST .../reports/{report_id}/findings/{finding_id}/skip-list`
- `GET .../skip-list`
- `POST .../skip-list`
- `PATCH .../skip-list/{source_finding_id}`
- `DELETE .../skip-list/{source_finding_id}`
- `POST .../skip-list/export`

**理由**：不复用的功能，没有保留价值。

### ScanFinding.in_skip_list 字段

**决定**：从 `ScanFinding` 数据类中移除 `in_skip_list` 字段。

**理由**：该字段的唯一用途是在前端展示"已加入"状态和控制按钮禁用。移除清单后，该字段无意义。前端 `ScanFindingResponse` 接口也将同步移除对应字段。

**注意**：旧报告中可能包含该字段，但 Python 的 `from_dict` 使用 `data.get("in_skip_list", False)` 默认值，多出的键不会被处理，不会导致反序列化错误。同理，JSON 序列化时不再输出该字段。

### 进度阶段调整

**决定**：从 `project_workspace.py` 的 `_project_progress_novel_summary` 中移除"跳读清单"阶段条目及 `skip_item_count` 计算。

**理由**：进度面板中该阶段始终为 0（除非用户手动添加过条目），移除后进度展示更简洁。

## Risks / Trade-offs

- **旧数据残留**：用户已有的 `skip_list.json` 文件不会被自动删除。这不会导致任何错误（代码不再读取它），但会占用磁盘空间。→ 风险很低，不做自动清理，用户可手动删除 `exports/{slug}/trigger_scan/skip_list.json`。
- **`in_skip_list` 字段兼容性**：旧报告 JSON 文件中可能包含 `in_skip_list: true`。Python 模型中的 `from_dict` 默认值为 `False`，多出的 JSON 键不会被处理，不会导致加载失败。前端类型同步移除后 TypeScript 编译也能保证一致性。
- **跳读建议保留的意义**：移除清单后，跳读建议仅作为内联提示存在，用户无法将其"保存到某处"。但建议本身仍有参考价值，且不影响扫描流程，保留成本极低。

## Migration Plan

1. 部署新版本后，旧 `skip_list.json` 文件不再被读取，但保留在磁盘上
2. 项目进度面板中不再显示"跳读清单"阶段
3. 雷点扫描工作台从 4 个标签页减少为 3 个
4. 无需数据迁移——旧格式的扫描报告可正常加载

## Open Questions

（无）
