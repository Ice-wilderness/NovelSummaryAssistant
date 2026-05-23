> **Git 提交约束**：每组任务（## 1 ~ ## 6）内的子任务全部完成后，立即提交一次 git commit，commit message 格式为 `feat(show-stage-progress): <本组任务简述>`。每组作为独立的功能增量提交，确保版本历史清晰可回溯。

## 1. 后端：小说总结结构化进度事件

- [ ] 1.1 在 `logic/utils.py` 中新增 `emit_stage_progress()` 函数，接受 stages 数组和 current_stage，构造 `event_type="progress"` 的 TaskEvent 并通过回调发射
- [ ] 1.2 在 `logic/orchestrator.py` 的 `async_orchestrator()` 中，在任务启动时计算完整阶段序列（根据 `use_fine_grained_flow` 确定阶段列表），并发射初始 stages 事件（所有阶段 completed=0, status=pending）
- [ ] 1.3 在 `logic/summarization_stages.py` 的 `run_small_summary_stage()` 中，每完成一个批次任务时发射进度事件，更新当前阶段的 completed 计数
- [ ] 1.4 在 `logic/summarization_stages.py` 的 `run_big_summary_stage()` 中，每完成一个大总结时发射进度事件
- [ ] 1.5 在 `logic/summarization_stages.py` 的 `run_super_summary_for_api()` 中，每完成一个超级总结时发射进度事件
- [ ] 1.6 在 `logic/summarization_stages.py` 的 `run_ultimate_summary_stage()` 中，每完成一个终极总结部分时发射进度事件
- [ ] 1.7 确保阶段间过渡时前一个阶段标记为 `completed`，下一个阶段标记为 `running`
- [ ] 1.8 **Git commit**: `feat(show-stage-progress): 后端小说总结结构化进度事件发射`

## 2. 后端：雷点扫描进度事件扩展

- [ ] 2.1 修改 `webui_backend/workflow_services.py` 中的 `create_trigger_scan_runner()`，在 precheck 阶段计算完整阶段序列（含 verification 阶段是否启用的判定），发射初始 stages 事件
- [ ] 2.2 修改 `_emit_scan_progress()` 函数，在 `data` 中新增 `stages` 数组和 `current_stage` 字段
- [ ] 2.3 在 precise_scan、verification、aggregation、reporting 各阶段的进度回调中，更新并发射完整的 stages 数组
- [ ] 2.4 **Git commit**: `feat(show-stage-progress): 后端雷点扫描进度事件补充 stages 数组`

## 3. 前端：StageProgressBar 组件

- [ ] 3.1 在 `frontend/src/components/` 下新建 `StageProgressBar.tsx`，接收 `stages: Stage[]` 和 `currentStage: string` props
- [ ] 3.2 实现水平进度条布局：每个阶段为一段，宽度按阶段数等分（或按 total 加权），用不同颜色表示 completed/running/pending
- [ ] 3.3 每个阶段段内显示 label 文本和 completed/total 数字（total 为 null 时显示省略号或等待图标）
- [ ] 3.4 当前运行阶段（status="running"）添加动画效果（脉冲或渐变）
- [ ] 3.5 添加响应式样式：窄屏时阶段段可水平滚动，label 不换行
- [ ] 3.6 导出 `StageProgressBar` 组件及 `Stage` 类型定义
- [ ] 3.7 **Git commit**: `feat(show-stage-progress): 前端 StageProgressBar 组件实现`

## 4. 前端：集成到小说总结页面

- [ ] 4.1 在 `NovelSummaryPage.tsx` 中引入 `StageProgressBar`，放置在项目控制区和任务控制按钮之间
- [ ] 4.2 页面加载时（有选中项目但无运行中任务），调用 `GET /api/projects/{slug}/progress` 获取文件系统进度，转换为 stages 数组并传入组件
- [ ] 4.3 任务运行期间，从 SSE 事件流中解析 `data.stages` 和 `data.current_stage`，实时更新组件状态
- [ ] 4.4 任务结束后，SSE 断开，回退请求文件系统进度并显示最终状态
- [ ] 4.5 **Git commit**: `feat(show-stage-progress): 前端小说总结页面集成 StageProgressBar`

## 5. 前端：集成到雷点扫描页面

- [ ] 5.1 在 `TriggerScanPage.tsx` 中引入 `StageProgressBar`，替换或增强现有的 `progress_text` 单行显示
- [ ] 5.2 页面加载时（有选中项目但无运行中任务），调用 `GET /api/projects/{slug}/progress` 获取触发扫描文件系统进度
- [ ] 5.3 任务运行期间，从 SSE 事件流中解析 `data.stages` 和 `data.current_stage`，实时更新组件状态
- [ ] 5.4 确保 StageProgressBar 与现有的"实时进度"事件列表和 findings 显示不冲突，形成上下层次的信息架构
- [ ] 5.5 **Git commit**: `feat(show-stage-progress): 前端雷点扫描页面集成 StageProgressBar`

## 6. 验证与收尾

- [ ] 6.1 端到端测试：启动小说总结任务，验证进度条从"小总结"到"终极总结"全阶段正确切换和计数
- [ ] 6.2 端到端测试：启动雷点扫描任务（含验证阶段），验证进度条阶段序列和实时更新
- [ ] 6.3 测试项目进入场景：选择历史项目，验证进度条立即显示已完成阶段、未完成阶段
- [ ] 6.4 测试边界情况：无项目选中时进度条隐藏、SSE 断线后回退到文件系统扫描、配置不启用验证时阶段列表不含验证阶段
- [ ] 6.5 检查 TypeScript 编译无错误，现有测试不受影响
- [ ] 6.6 **Git commit**: `feat(show-stage-progress): 端到端验证与收尾`
