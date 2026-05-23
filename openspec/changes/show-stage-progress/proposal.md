## Why

当前小说总结和雷点扫描的各阶段进度不透明，用户进入项目后无法一眼看清整体进展——不知道当前处于哪个阶段、当前阶段还剩多少未完成、总共还有几个阶段等待执行。小说总结仅通过文本日志描述进度，雷点扫描虽有结构化进度事件但前端仅展示单行文本，缺少涵盖所有阶段的进度条可视化。

## What Changes

- 后端为**小说总结**工作流新增结构化阶段进度事件（含 stage、completed、total），使进度信息从日志文本中分离并可被前端消费
- 后端为**雷点扫描**工作流扩充阶段进度事件，使其与小说总结统一数据结构
- 前端新增**阶段进度条组件**（StageProgressBar），在项目页面顶部显示所有阶段的横向进度条，标注当前阶段、已完成阶段、未开始阶段
- 前端**实时更新**：任务运行期间通过 SSE 事件实时更新进度条中的 completed/total，任务结束后通过 `ProjectProgressPanel` 文件系统扫描结果回填
- **进入项目即显示**：加载历史项目或导入项目时，立即依据缓存/文件系统状态计算并显示当前进度，无需等待任务启动

## Capabilities

### New Capabilities
- `stage-progress-visualization`: 前端阶段进度条组件，涵盖小说总结和雷点扫描的所有阶段，支持实时更新与静态回填

### Modified Capabilities
- `webui-workbench`: "Live Logs And Progress" 需求新增阶段进度条子需求——进度条 SHALL 显示完整阶段序列、当前阶段高亮、各阶段完成数/总数
- `task-runtime-api`: "Realtime Event Stream" 需求新增小说总结结构化阶段进度事件子需求；"Structured Trigger Scan Events" 需求扩展以统一两种工作流的进度事件字段
- `trigger-scan-workflow`: "Realtime Scan Progress" 需求扩展，要求进度事件携带完整阶段序列信息供前端进度条消费

## Impact

- **后端**：`logic/orchestrator.py` 和 `logic/summarization_stages.py` 需在各阶段开始时发射结构化进度事件；`webui_backend/workflow_services.py` 中 `_emit_scan_progress` 需补充 stages 序列信息
- **前端**：新增 `StageProgressBar` 组件；修改 `NovelSummaryPage.tsx` 和 `TriggerScanPage.tsx` 以集成进度条；修改 `ProjectProgressPanel` 以支持实时更新
- **数据流**：`TaskEvent` 的 `data` 字段新增 `stages` 和 `current_stage` 键，前端通过 SSE 流消费
