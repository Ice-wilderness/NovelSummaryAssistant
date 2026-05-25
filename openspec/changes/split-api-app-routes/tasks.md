## 1. Baseline and Route Context

- [x] 1.1 Add or update a route parity test that captures the required public WebUI API method/path set exposed by `create_app(...)`.
- [x] 1.2 Create the `webui_backend/routes/` package and a lightweight shared route context without moving route behavior yet.
- [x] 1.3 Run the route parity test and `python -m pytest tests/test_api_app.py -q`.
- [x] 1.4 Commit the baseline/context block after tests pass.

## 2. Low-Coupling API Routes

- [x] 2.1 Move health, API config, user settings, prompt template/workflow, and model-list routes into modular route registration.
- [x] 2.2 Move trigger profile and chapter pattern config routes into modular route registration.
- [x] 2.3 Run `python -m pytest tests/test_api_app.py tests/test_trigger_profile_service.py -q`.
- [x] 2.4 Commit the low-coupling routes block after tests pass.

## 3. Project, Upload, and Local Path Routes

- [x] 3.1 Move browse, upload, project metadata, project update/delete, output migration check, open-directory, and path resolve routes into modular route registration.
- [x] 3.2 Keep project response shaping, upload resolution, and output directory selection behavior equivalent to the current app.
- [x] 3.3 Run `python -m pytest tests/test_api_app.py tests/test_project_workspace.py -q`.
- [x] 3.4 Commit the project/upload/path routes block after tests pass.

## 4. Trigger Scan Routes

- [x] 4.1 Move trigger scan precheck, project scan config, task start/status, report list/detail/delete/update/context/export routes into modular route registration.
- [x] 4.2 Preserve scan startup validation, report store resolution, resume metadata, and existing warning/error response behavior.
- [x] 4.3 Run `python -m pytest tests/test_api_app.py tests/test_trigger_scan_pipeline.py tests/test_trigger_scan_reporting.py -q`.
- [x] 4.4 Commit the trigger scan routes block after tests pass.

## 5. Summary, Splitter, and Task Runtime Routes

- [x] 5.1 Move novel summary, small-summary preparation, article summary, custom summary, split preview, direct splitter, and splitter task routes into modular route registration.
- [x] 5.2 Move task list/detail/pause/resume/cancel/events routes into modular route registration while preserving SSE event behavior.
- [x] 5.3 Run `python -m pytest tests/test_api_app.py tests/test_task_runtime.py tests/test_article_summary_logic.py tests/test_chapter_granularity.py -q`.
- [x] 5.4 Commit the summary/splitter/task runtime routes block after tests pass.

## 6. Cleanup and Final Verification

- [ ] 6.1 Remove imports, helper functions, or route-local code made unused by the split while keeping unrelated code unchanged.
- [ ] 6.2 Confirm `create_app(...)` remains the stable application assembly entry point and clearly registers all route groups plus static frontend fallback.
- [ ] 6.3 Run `python -m pytest`.
- [ ] 6.4 Run `npm run build` if any frontend contract, generated type expectation, or static-serving behavior was touched.
- [ ] 6.5 Commit the cleanup/final verification block after checks pass.
