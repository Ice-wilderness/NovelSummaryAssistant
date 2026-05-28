# 测试与质量保障审计

## 当前测试基线

- `python -m pytest`：287 passed。
- `npm run test`（`frontend/`）：51 passed。
- `npm run build`：TypeScript 检查和 Vite 构建通过。

## 覆盖观察

Python 测试覆盖面较广，已有测试包括：

- API 路由：`tests/test_api_app.py`
- 配置服务：`tests/test_config_service.py`
- 项目工作区：`tests/test_project_workspace.py`
- 任务运行时：`tests/test_task_runtime.py`
- LLM API：`tests/test_llm_api.py`
- 总结逻辑：`tests/test_article_summary_logic.py`、`tests/test_custom_summary_logic.py`、`tests/test_small_summary_only.py`
- 状态恢复：`tests/test_state_manager_resume.py`
- 雷点扫描：`tests/test_trigger_scan_pipeline.py`、`tests/test_trigger_scan_reporting.py`、`tests/test_trigger_scan_prompts.py`
- 章节边界与章节粒度：`tests/test_chapter_boundaries.py`、`tests/test_chapter_granularity.py`

覆盖亮点：

- `tests/test_api_app.py` 覆盖上传、项目保存、任务启动、雷点扫描、目录解析和历史项目等主要 API。
- `tests/test_project_workspace.py` 覆盖托管工作区、导出目录、导入旧项目、章节粒度兼容和删除保护。
- `tests/test_trigger_scan_pipeline.py` 覆盖扫描启动校验、批次构建、模型 JSON 解析、验证批次、聚合和续扫状态。
- `tests/test_llm_api.py` 覆盖提示词消息渲染、错误分类、失败日志、最小输出长度重试和结构化消息调用。
- `tests/test_state_manager_resume.py` 覆盖部分恢复判断和导入旧输出的兼容逻辑。
- `tests/test_chapter_boundaries.py` 覆盖默认/正则/标题列表共享边界解析、raw regex 保护和结构化失败。
- `tests/test_task_runtime.py` 覆盖任务摘要持久化、重启后终态摘要加载、非终态任务恢复为 `interrupted` 和无效摘要容错。
- `split-logic-utils` 已通过 focused tests 和完整 `python -m pytest` 验证 `logic.utils` 兼容门面与 focused helper 模块拆分。
- `add-summary-partial-status` 已通过 focused tests 验证 `TaskRunOutcome`、文章总结 section partial、自定义总结素材 partial、API/项目历史 partial 状态和前端 summary partial warning 展示。
- `frontend/src/views/trigger-scan/*.test.*` 覆盖雷点扫描 display helpers、profile draft、result filters、ProfileTab、ScanConfigTab、ResultsTab 和 ContextModal。
- `frontend/src/views/SummaryPartialNotice.test.tsx` 覆盖文章/自定义总结 partial warning、失败输入详情、保留结果和旧记录缺少详情时的 fallback 展示。
- `frontend/src/api/client.test.ts` 覆盖成功 JSON、JSON 错误、非 JSON 错误和 splitter task API client 请求路径。
- `frontend/src/hooks/useManagedProject.test.tsx` 与 `frontend/src/views/NovelSummaryPage.test.tsx` 覆盖 100 MB 上传大小预检、读取前拒绝、小说页分割任务成功路径和分割失败状态保留。
- `frontend/src/views/SplitterPage.test.tsx` 覆盖章节分割页预览/direct split 失败提示和源文件保留。
- `frontend/src/components/layout/AppLayout.test.tsx` 与 `frontend/src/components/forms/FormControls.test.tsx` 覆盖 `interrupted` 任务状态、禁用任务控制和历史项目状态展示。
- `tests/test_config_service.py`、`tests/test_project_workspace.py` 和 `tests/test_api_app.py` 覆盖配置损坏 `.bak` 备份/warning、备份失败、自定义输出目录 strict 拒绝、历史读取 compat warning、显式默认目录回退、`open_directory` 输出目录边界和本地 picker/open 错误归一化。
- `frontend/src/views/ApiConfigPage.test.tsx`、`frontend/src/components/patterns/PatternSelector.test.tsx`、`frontend/src/hooks/useManagedProject.test.tsx` 和 `frontend/src/components/forms/FormControls.test.tsx` 覆盖局部配置 warning、无效输出目录错误展示、保留无效路径编辑、默认目录回退按钮和本地能力错误位置。

## 发现

### 已部分治理：缺少前端自动化测试

- 原始现象：前端只有 TypeScript 构建验证，没有组件测试或交互测试。
- 当前状态：已新增 `npm run test`，使用 Vitest + Testing Library；雷点扫描页面拆分边界、summary partial warning、API client 错误解析、上传大小预检、小说页分割任务路径、章节分割失败提示和 `interrupted` 状态展示已有 focused tests。
- 剩余影响：任务订阅重连/状态兜底和跨页面交互仍缺少系统化测试。
- 当前风险级别：中。
- 建议：沿用现有测试基础，优先补 `useTaskActions` SSE 兜底、核心页面流和真实浏览器长任务交互测试。

### 已部分治理：取消/暂停/续扫边界测试不足

- 原始现象：已有 `test_task_runtime.py` 覆盖运行时基础状态，但没有覆盖每个业务 runner 如何传播取消和暂停。
- 当前状态：`tests/test_workflow_services.py` 已覆盖小说/文章/自定义总结、分割和雷点扫描 runner 的取消传播，覆盖雷点扫描 pause blocking、resume progress、历史 finding 验证和 partial failed；`tests/test_task_runtime.py` 与 `tests/test_api_app.py` 已覆盖轻量任务摘要持久化、后端重启后的终态查询和 `interrupted` 中断状态。
- 剩余影响：完整任务事件日志、`Last-Event-ID` 回放、SSE heartbeat 和真实浏览器长任务交互仍缺少系统化测试。
- 当前风险级别：中。
- 建议：下一步围绕完整事件回放协议、SSE heartbeat、非小说工作流深度 repair 和浏览器交互兜底补测试。

### 已部分治理：部分成功和数据完整性测试不足

- 现象：文章总结 section 级失败后可能继续生成最终总结，雷点扫描部分失败也可能生成 completed 状态报告。
- 当前状态：雷点扫描 `partial_failed`、report warning 和前端 warning 展示已有服务层/前端 focused tests；文章总结和自定义总结已补 `partial_failed`、warning、失败输入详情、API/项目历史响应和前端展示 tests；章节分割失败时保留既有 uploads/inputs 已有项目工作区和 API tests。
- 当前状态：状态文件与输出文件 reconcile、导入旧项目后的异常状态展示和小说总结 repair flow 已补后端/API/前端 focused tests。
- 剩余影响：非小说工作流的深度 repair、完整浏览器交互和更系统化端到端覆盖仍可继续补强。
- 当前风险级别：中。
- 建议：下一步围绕非小说 workflow repair、安全覆盖边界和真实浏览器长任务交互补测试。

### 已部分治理：OpenSpec 契约和实现漂移缺少自动检查

- 现象：OpenSpec 有较完整能力契约，但实现是否满足契约主要靠人工和测试命名间接保证。
- 原始证据：聚合提示词契约和实现不一致未被测试捕获。
- 当前状态：聚合提示词契约已澄清为 deterministic aggregation，`trigger-scan-page-modularity` 主规格已同步；但高价值规格与测试文件之间仍没有统一映射索引。
- 当前风险级别：中。
- 建议：为高价值契约增加 spec-to-test 映射清单，归档 change 时同步记录验证命令和对应测试文件。

## 优化空间

- 前端测试已具备最小工具链；后续新增前端行为时优先补同目录 focused tests，避免只依赖构建。
- 为长任务控制写行为级测试，不只测试 `TaskRuntime` 单体。
- 将验证命令写入 README 或贡献文档，降低接手成本。
- 将高风险 OpenSpec 条目和测试文件建立映射，减少规格和实现长期漂移。

## 验证记录

```text
python -m pytest
287 passed in 8.14s
```

```text
npm run test
17 test files passed; 51 tests passed.
```

```text
npm run build
TypeScript checks passed; Vite production build completed.
```

```text
openspec validate --all
21 passed; 0 failed.
```
