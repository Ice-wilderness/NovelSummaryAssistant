## Context

当前项目有两个主要长任务工作流：小说总结（`novel_summary`）和雷点扫描（`trigger_scan`）。两者的进度展示存在以下问题：

- **小说总结**：`orchestrator.py` 和 `summarization_stages.py` 仅通过 `log_message()` 发送文本日志（如 `"--- API: 开始小总结阶段，有 50 个待处理章节 ---"`），没有结构化进度数据。前端只能显示日志文本，无法渲染进度条。
- **雷点扫描**：`workflow_services.py` 中的 `_emit_scan_progress()` 已发射带 `stage`、`completed`、`total` 的结构化事件，但前端 `TriggerScanPage.tsx` 仅显示 `progress_text` 字符串，没有可视化的阶段进度条。
- **项目进度面板**：`ProjectProgressPanel` 通过 `scan_project_progress()` 扫描文件系统计算进度，运行期间不更新。用户首次进入项目时，该面板虽能显示离线进度，但样式简陋且不与实时任务事件联动。

两个工作流共用 `TaskEvent`（`event_type`、`progress_text`、`data`）和 SSE 事件流，但进度信息的结构化程度不一致。

## Goals / Non-Goals

**Goals:**
- 统一小说总结和雷点扫描的结构化阶段进度事件格式，使 `TaskEvent.data` 包含完整的 `stages` 数组
- 新增 `StageProgressBar` 前端组件，横向展示所有阶段及各自的 completed/total
- 进入项目时立即显示进度（从文件系统/缓存计算初始状态）
- 任务运行时通过 SSE 事件实时更新进度条
- 复用现有 `TaskEvent` 和 SSE 管道，不引入新的通信机制

**Non-Goals:**
- 不改变任务暂停/恢复/取消的底层机制
- 不修改 `ProjectProgressPanel` 的文件系统扫描逻辑（仅改进其前端展示）
- 不改变触发扫描的 resume/checkpoint 行为
- 不添加进度持久化（任务结束后进度由文件系统扫描反推即可）

## Decisions

### Decision 1: 进度事件数据格式

在每个阶段级进度事件中携带完整 `stages` 数组，而非增量更新。

**选择**：每次 `event_type="progress"` 事件（阶段粒度）的 `data` 字段包含：

```json
{
  "stages": [
    {"id": "small_summary", "label": "小总结", "completed": 45, "total": 50, "status": "completed"},
    {"id": "big_summary_plot", "label": "大总结-剧情", "completed": 3, "total": 5, "status": "running"},
    {"id": "big_summary_char", "label": "大总结-角色", "completed": 0, "total": 5, "status": "pending"},
    ...
  ],
  "current_stage": "big_summary_plot"
}
```

**理由**：
- 前端无需维护阶段状态机，每次事件直接替换渲染数据，避免状态漂移
- 阶段数量最多 8 个，每条 JSON 仅数百字节，无性能问题
- 事件丢失时下一帧自动修复（自愈性）

**替代方案**：增量事件（每次只发当前阶段的 completed/total），前端累积状态。缺点：前端需要知道所有阶段定义，且事件丢失会导致进度条冻结。

### Decision 2: 阶段序列由后端在任务启动时确定

阶段列表取决于运行时配置（如是否启用验证、是否精细粒度模式），由后端在任务启动时计算并随第一个进度事件发送。

**理由**：
- 前端无需根据配置推导阶段序列，保持纯展示逻辑
- 后端是配置和阶段的权威来源
- 第一个事件即包含完整 stages 数组，前端可立即渲染完整进度条框架

### Decision 3: 组件位置与集成方式

`StageProgressBar` 组件放置在项目页面顶部、表单控制区与日志区之间，作为 `NovelSummaryPage` 和 `TriggerScanPage` 的共享组件。

**布局**：
```
┌─────────────────────────────────────────────┐
│ 项目控制区（项目选择、文件上传、配置表单）      │
├─────────────────────────────────────────────┤
│ ████████████░░░░░░░░░░░░░░░░░░░░  阶段进度条  │  ← 新增
│ 小总结 ✓ | 大总结-剧情 ● | 大总结-角色 ○ | ... │
├─────────────────────────────────────────────┤
│ 任务控制按钮（开始/暂停/取消）                 │
├─────────────────────────────────────────────┤
│ 日志面板 / 结果面板                           │
└─────────────────────────────────────────────┘
```

**理由**：
- 进度条是用户进入页面后最想看到的信息，放在顶部确保可见性
- 与现有 `ProjectProgressPanel` 不冲突——`ProjectProgressPanel` 的离线文件扫描数据用于初始化 `StageProgressBar` 的静态状态

### Decision 4: 初始进度来源

进入项目时，调用 `GET /api/projects/{slug}/progress`（已有端点，返回 `ProjectProgressPanel` 数据）获取离线计算的阶段进度，填充 `StageProgressBar` 初始值。任务运行时切换为 SSE 事件驱动更新。

**两种数据源无缝切换**：
1. 页面加载 → 请求 `/api/projects/{slug}/progress` → 渲染静态进度条
2. 任务启动 → SSE 连接建立 → 收到第一个 `progress` 事件（含 stages 数组） → 切换为实时模式
3. 任务结束 → SSE 连接关闭 → 再次请求文件系统进度作为最终状态

### Decision 5: 小说总结后端改动范围

在 `logic/summarization_stages.py` 各阶段函数中，阶段开始时和每完成一个子任务时发射结构化进度事件。不在 `orchestrator.py` 中集中处理，而是在各阶段函数内部发射，因为阶段函数最清楚 completed/total。

需要修改 `log_message()` 或在阶段函数中新增 `emit_progress()` 调用。由于 `log_message()` 当前只发送文本，需要扩展或新增方法。

**选择**：在 `logic/utils.py` 中新增 `emit_stage_progress()` 函数，接受 stages 数组，通过现有的 `event_queue` 回调发射。阶段函数通过参数接收此回调。

## Risks / Trade-offs

- **前端状态切换**：SSE 连接断开时进度条可能短暂显示过时数据 → 在 SSE 断开时自动回退到文件系统扫描结果
- **阶段定义变更**：如果未来新增或删除阶段，后端 stages 数组自动反映，前端只需渲染，无需改动
- **初始加载延迟**：`/api/projects/{slug}/progress` 需要扫描文件系统，大量文件时可能较慢（当前已有此端点，性能已可接受）
