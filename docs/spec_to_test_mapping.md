# OpenSpec 到测试映射

本文是维护导航，不是覆盖率证明。修改相关能力时，优先运行表中的 focused tests，再按风险运行全量 `python -m pytest`、`npm run test`、`npm run build` 和 `openspec validate --all`。

## 基线命令

在项目根目录运行：

```powershell
python -m pytest
openspec validate --all
```

在 `frontend/` 目录运行：

```powershell
npm run test
npm run build
```

## 高价值规格映射

| 能力规格 | 代表性覆盖 | 推荐 focused 验证 |
| --- | --- | --- |
| `openspec/specs/task-runtime-api/spec.md` | `tests/test_task_runtime.py`、`tests/test_api_app.py`、`tests/test_workflow_services.py`、`frontend/src/api/client.test.ts`、`frontend/src/hooks/useTaskActions.test.tsx`、`frontend/src/components/layout/AppLayout.test.tsx` | `python -m pytest tests/test_task_runtime.py tests/test_api_app.py tests/test_workflow_services.py`；`cd frontend; npm run test -- src/api/client.test.ts src/hooks/useTaskActions.test.tsx src/components/layout/AppLayout.test.tsx` |
| `openspec/specs/managed-project-outputs/spec.md` | `tests/test_project_workspace.py`、`tests/test_api_app.py`、`frontend/src/views/NovelSummaryPage.test.tsx`、`frontend/src/components/forms/FormControls.test.tsx` | `python -m pytest tests/test_project_workspace.py tests/test_api_app.py`；`cd frontend; npm run test -- src/views/NovelSummaryPage.test.tsx src/components/forms/FormControls.test.tsx` |
| `openspec/specs/configuration-management/spec.md` | `tests/test_config_service.py`、`tests/test_api_app.py`、`frontend/src/views/ApiConfigPage.test.tsx`、`frontend/src/components/patterns/PatternSelector.test.tsx`、`frontend/src/components/forms/FormControls.test.tsx` | `python -m pytest tests/test_config_service.py tests/test_api_app.py`；`cd frontend; npm run test -- src/views/ApiConfigPage.test.tsx src/components/patterns/PatternSelector.test.tsx src/components/forms/FormControls.test.tsx` |
| `openspec/specs/file-upload-workflow/spec.md` | `tests/test_api_app.py`、`tests/test_project_workspace.py`、`frontend/src/hooks/useManagedProject.test.tsx`、`frontend/src/views/NovelSummaryPage.test.tsx`、`frontend/src/api/client.test.ts` | `python -m pytest tests/test_api_app.py tests/test_project_workspace.py`；`cd frontend; npm run test -- src/hooks/useManagedProject.test.tsx src/views/NovelSummaryPage.test.tsx src/api/client.test.ts` |
| `openspec/specs/trigger-scan-workflow/spec.md`、`openspec/specs/trigger-scan-results/spec.md`、`openspec/specs/trigger-profile-management/spec.md` | `tests/test_trigger_scan_pipeline.py`、`tests/test_trigger_scan_reporting.py`、`tests/test_trigger_scan_prompts.py`、`tests/test_trigger_profile_service.py`、`tests/test_trigger_models.py`、`tests/test_workflow_services.py`、`frontend/src/views/trigger-scan/*.test.*` | `python -m pytest tests/test_trigger_scan_pipeline.py tests/test_trigger_scan_reporting.py tests/test_trigger_scan_prompts.py tests/test_trigger_profile_service.py tests/test_trigger_models.py tests/test_workflow_services.py`；`cd frontend; npm run test -- src/views/trigger-scan` |
| `openspec/specs/summary-partial-status/spec.md` | `tests/test_task_runtime.py`、`tests/test_article_summary_logic.py`、`tests/test_custom_summary_logic.py`、`tests/test_workflow_services.py`、`tests/test_api_app.py`、`frontend/src/views/SummaryPartialNotice.test.tsx` | `python -m pytest tests/test_task_runtime.py tests/test_article_summary_logic.py tests/test_custom_summary_logic.py tests/test_workflow_services.py tests/test_api_app.py`；`cd frontend; npm run test -- src/views/SummaryPartialNotice.test.tsx` |
| `openspec/specs/chapter-processing-granularity/spec.md`、`openspec/specs/split-preview/spec.md`、`openspec/specs/chapter-pattern-config/spec.md`、`openspec/specs/chapter-splitting-integration/spec.md` | `tests/test_chapter_boundaries.py`、`tests/test_chapter_granularity.py`、`tests/test_project_workspace.py`、`tests/test_api_app.py`、`tests/test_workflow_services.py`、`frontend/src/views/SplitterPage.test.tsx`、`frontend/src/views/NovelSummaryPage.test.tsx`、`frontend/src/components/patterns/PatternSelector.test.tsx` | `python -m pytest tests/test_chapter_boundaries.py tests/test_chapter_granularity.py tests/test_project_workspace.py tests/test_api_app.py tests/test_workflow_services.py`；`cd frontend; npm run test -- src/views/SplitterPage.test.tsx src/views/NovelSummaryPage.test.tsx src/components/patterns/PatternSelector.test.tsx` |
| `openspec/specs/workflow-prompt-composition/spec.md` | `tests/test_llm_api.py`、`tests/test_trigger_scan_prompts.py`、提示词编辑器当前主要由构建和手工检查兜底 | `python -m pytest tests/test_llm_api.py tests/test_trigger_scan_prompts.py`；`cd frontend; npm run build` |
| `openspec/specs/webui-api-route-modularity/spec.md` | `tests/test_api_app.py` 中的 route table parity 和 API 行为测试 | `python -m pytest tests/test_api_app.py` |
| `openspec/specs/project-workspace-service-modularity/spec.md` | `tests/test_project_workspace.py`、`tests/test_api_app.py`、`tests/test_imports.py` | `python -m pytest tests/test_project_workspace.py tests/test_api_app.py tests/test_imports.py` |
| `openspec/specs/logic-utils-modularity/spec.md` | `tests/test_utils.py`、`tests/test_imports.py`、核心 workflow focused tests | `python -m pytest tests/test_utils.py tests/test_imports.py tests/test_article_summary_logic.py tests/test_custom_summary_logic.py tests/test_chapter_boundaries.py` |
| `openspec/specs/trigger-scan-page-modularity/spec.md` | `frontend/src/views/trigger-scan/*.test.*`、`frontend/src/views/TriggerScanPage.tsx` 通过 build/typecheck 兜底 | `cd frontend; npm run test -- src/views/trigger-scan && npm run build` |
| `openspec/specs/webui-workbench/spec.md`、`openspec/specs/stage-progress-visualization/spec.md` | `frontend/src/components/forms/FormControls.test.tsx`、`frontend/src/components/layout/AppLayout.test.tsx`、`frontend/src/views/NovelSummaryPage.test.tsx`、`tests/test_webui_e2e.py` | `python -m pytest tests/test_webui_e2e.py`；`cd frontend; npm run test -- src/components/forms/FormControls.test.tsx src/components/layout/AppLayout.test.tsx src/views/NovelSummaryPage.test.tsx` |
| `openspec/specs/module-stability-audit-reports/spec.md` | `docs/stability_audit/` 文档和 OpenSpec 校验 | `openspec validate --all`，并人工检查审计文档链接和当前状态 |
| `openspec/specs/maintainer-runtime-documentation/spec.md` | `README.md`、`docs/runtime_behavior_notes.md`、`docs/spec_to_test_mapping.md`、`docs/archived_changes_index.md`、OpenSpec 校验 | `openspec validate --all`，并人工检查 README/docs 链接、运行时规则、规格映射和归档索引 |

## 使用约定

- 表格中的 tests 是代表性入口，不是完整覆盖清单。
- 新增或修改主规格时，应同步更新本映射。
- 归档 change 时，应记录实际运行过的 focused tests 和全量验证命令。
- 对跨模块行为，先运行 focused tests，再运行全量后端、前端和 OpenSpec 校验。
