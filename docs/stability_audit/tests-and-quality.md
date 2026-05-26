# 测试与质量保障审计

## 当前测试基线

- `python -m pytest`：217 passed。
- `npm run test`（`frontend/`）：20 passed。
- `npm run build`：TypeScript 检查和 Vite 构建通过。

## 覆盖观察

Python 测试覆盖面较广，已有测试包括：

- API 路由：`tests/test_api_app.py`
- 配置服务：`tests/test_config_service.py`
- 项目工作区：`tests/test_project_workspace.py`
- 任务运行时：`tests/test_task_runtime.py`
- LLM API：`tests/test_llm_api.py`
- 总结逻辑：`tests/test_article_summary_logic.py`、`tests/test_small_summary_only.py`
- 状态恢复：`tests/test_state_manager_resume.py`
- 雷点扫描：`tests/test_trigger_scan_pipeline.py`、`tests/test_trigger_scan_reporting.py`、`tests/test_trigger_scan_prompts.py`
- 章节粒度：`tests/test_chapter_granularity.py`

覆盖亮点：

- `tests/test_api_app.py` 覆盖上传、项目保存、任务启动、雷点扫描、目录解析和历史项目等主要 API。
- `tests/test_project_workspace.py` 覆盖托管工作区、导出目录、导入旧项目、章节粒度兼容和删除保护。
- `tests/test_trigger_scan_pipeline.py` 覆盖扫描启动校验、批次构建、模型 JSON 解析、验证批次、聚合和续扫状态。
- `tests/test_llm_api.py` 覆盖提示词消息渲染、错误分类、失败日志、最小输出长度重试和结构化消息调用。
- `tests/test_state_manager_resume.py` 覆盖部分恢复判断和导入旧输出的兼容逻辑。
- `frontend/src/views/trigger-scan/*.test.*` 覆盖雷点扫描 display helpers、profile draft、result filters、ProfileTab、ScanConfigTab、ResultsTab 和 ContextModal。

## 发现

### 已部分治理：缺少前端自动化测试

- 原始现象：前端只有 TypeScript 构建验证，没有组件测试或交互测试。
- 当前状态：已新增 `npm run test`，使用 Vitest + Testing Library；雷点扫描页面拆分边界已有 focused tests。
- 剩余影响：API client、上传、任务订阅和跨页面交互仍缺少系统化测试。
- 当前风险级别：中。
- 建议：沿用现有测试基础，优先补 `requestJson` 非 JSON 错误、`useManagedProject` 上传大小预检、`useTaskActions` SSE 兜底和核心页面流。

### 已部分治理：取消/暂停/续扫边界测试不足

- 原始现象：已有 `test_task_runtime.py` 覆盖运行时基础状态，但没有覆盖每个业务 runner 如何传播取消和暂停。
- 当前状态：`tests/test_workflow_services.py` 已覆盖小说/文章/自定义总结、分割和雷点扫描 runner 的取消传播，覆盖雷点扫描 pause blocking、resume progress、历史 finding 验证和 partial failed。
- 剩余影响：任务运行时事件持久化、后端重启恢复、last-event-id 回放和真实浏览器长任务交互仍缺少系统化测试。
- 当前风险级别：中。
- 建议：下一步围绕 terminal task summary、SSE heartbeat/回放和浏览器交互兜底补测试。

### 已部分治理：部分成功和数据完整性测试不足

- 现象：文章总结 section 级失败后可能继续生成最终总结，雷点扫描部分失败也可能生成 completed 状态报告。
- 当前状态：雷点扫描 `partial_failed`、report warning 和前端 warning 展示已有服务层/前端 focused tests；文章总结 partial success 仍未定义用户可见状态和 warning。
- 剩余影响：文章总结最终产物仍可能缺失 section 而用户不易察觉。
- 当前风险级别：中。
- 建议：为文章总结 partial 状态、失败 section 列表、最终报告 warning 和是否继续生成终稿补服务层测试。

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
217 passed in 4.11s
```

```text
npm run test
8 test files passed; 20 tests passed.
```

```text
npm run build
TypeScript checks passed; Vite production build completed.
```
