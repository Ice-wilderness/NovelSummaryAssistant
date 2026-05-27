## Implementation Notes

### Product Semantics

- Task lifecycle status records what the last task did: `success`, `partial_failed`, `failed`, `cancelled`, `interrupted`, and related running states remain task facts.
- Project reconciliation status records whether the current files still match that history:
  - `ok`: recorded completion/partial completion and required outputs are present.
  - `incomplete`: no reliable completion record and no generated completion output.
  - `abnormal_completed`: completion or partial completion was recorded, but current required outputs are missing, unreadable, or format-inconsistent.
  - `state_incomplete`: generated outputs exist, but metadata/task summary is not reliable enough to call it normal completion.
  - `unsupported`: the workflow has no first-round repair implementation.
- `project_repair` is a separate task type. It does not rewrite the original task into failed/incomplete and does not auto-resume abnormal projects.

### Repair Scope

- No-LLM repair is limited to metadata/progress/index/path/cache-location reconciliation and does not generate or rewrite summary text.
- Any repair that creates or replaces small-summary, big-summary, super-summary, ultimate-summary, article-summary, or custom-summary text is treated as LLM repair and requires explicit confirmation for LLM usage and possible content variance.
- First-round executable content repair is limited to novel summary missing-stage reruns when source chapter files, saved settings, and API configuration are available.
- Unsupported workflows or unsafe missing inputs return blocked repair actions instead of silently broadening the rerun.

### Verification

- `python -m pytest tests/test_project_workspace.py tests/test_api_app.py::ApiAppTests::test_public_api_route_table_matches_expected_contract tests/test_api_app.py::ApiAppTests::test_project_repair_plan_reports_abnormal_completed_action tests/test_api_app.py::ApiAppTests::test_project_repair_rejects_llm_action_without_confirmation tests/test_api_app.py::ApiAppTests::test_project_repair_rejects_stale_action_id tests/test_api_app.py::ApiAppTests::test_project_repair_rejects_blocked_action tests/test_api_app.py::ApiAppTests::test_project_metadata_repair_starts_separate_task tests/test_api_app.py::ApiAppTests::test_project_summary_repair_starts_llm_rerun_task -q`
- `npm test -- NovelSummaryPage.test.tsx FormControls.test.tsx`
- `npm run typecheck`
- `python -m pytest -q`
- `npm test`
- `npm run build`
- `openspec validate --all`
