# Implementation Notes

## Test Extension Map

- Task runtime and terminal events: extend `tests/test_task_runtime.py` for accepted cancellation, terminal event emission, and stream completion behavior.
- Business runner cancellation: extend `tests/test_workflow_services.py` and targeted API tests in `tests/test_api_app.py` to cover novel, article, custom, chapter split, and trigger scan runner cancellation propagation.
- Trigger scan pause/resume/progress: extend `tests/test_trigger_scan_pipeline.py` for state helpers and add workflow-service level tests where API-call pause gating and cumulative progress are observable.
- Trigger scan reports: extend `tests/test_trigger_scan_reporting.py` for `partial_failed`, warnings, old-report compatibility, and preserved partial artifacts.
- Project output ownership: extend `tests/test_project_workspace.py` and API deletion tests in `tests/test_api_app.py` for managed ownership metadata, custom output preservation, missing metadata preservation, and response details.
- API diagnostics: extend `tests/test_llm_api.py` for complete non-secret input/output preservation, secret redaction, and cleanup/retention behavior.
- Prompt aggregation contract: extend `tests/test_trigger_scan_prompts.py`, `tests/test_config_service.py`, and prompt editor/API assertions to verify precise/verification prompt nodes remain active while aggregation is deterministic.
- Frontend status recovery: update build-time TypeScript surfaces in `frontend/src/hooks/useTaskActions.ts`, `frontend/src/api/types.ts`, and trigger scan display code; add focused frontend tests only if a frontend test harness exists during implementation.
