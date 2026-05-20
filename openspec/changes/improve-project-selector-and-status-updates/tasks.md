## 1. Backend Project Deletion

- [x] 1.1 Add `ProjectWorkspaceService.delete_project(project_slug)` to validate the project, delete `workspace/projects/<slug>`, delete the managed export directory recorded for that project, and leave any external project-level custom output directory untouched.
- [x] 1.2 Add `DELETE /api/projects/{project_slug}` in `webui_backend/api_app.py`, returning a small success payload and clear errors for missing or invalid projects.
- [x] 1.3 Add backend tests in `tests/test_project_workspace.py` and `tests/test_api_app.py` for successful deletion, missing project errors, history removal, and custom output preservation.

## 2. User Default Export Directory

- [x] 2.1 Add a persisted user settings model/service for `default_export_directory`, with load/save defaults that preserve existing config compatibility.
- [x] 2.2 Add backend API operations to load, save, clear, and validate the user-level default export directory.
- [x] 2.3 Update managed output resolution so the effective directory priority is project-level custom directory, then user-level default export directory, then current fallback default export directory.
- [x] 2.4 Add backend tests for output directory priority, invalid user-level directory rejection, clearing the setting, and fallback behavior.

## 3. Frontend API And Project State

- [x] 3.1 Add `apiClient.deleteProject(projectSlug)` and user settings API methods, plus any needed response type updates in `frontend/src/api/client.ts` and `frontend/src/api/types.ts`.
- [x] 3.2 Extend `useManagedProject` with `startNewProject`, `deleteProject`, and a reusable state reset path that clears selected project, uploads, output directories, progress, messages, and errors.
- [x] 3.3 Ensure deleting the currently selected project refreshes history and returns the page to the fresh-project state.
- [x] 3.4 Ensure workflow pages display the effective output directory after user-level default export directory changes.

## 4. Status Refresh On Task Completion

- [x] 4.1 Wire task terminal-state handling so a managed workflow refreshes its project list and current project details after `success`, `failed`, or `cancelled` without requiring a browser reload.
- [x] 4.2 Ensure the refresh path updates `latest_task_status` and progress for the active project as well as the historical project list.
- [x] 4.3 Add focused tests or a documented manual verification path covering a managed task reaching terminal state and the history status updating in-place.

## 5. Project History And Settings UI

- [x] 5.1 Replace the current history `<select>` behavior with a control that shows each project with a leading status label, independent project name text, workflow/update metadata, restore action, and delete action.
- [x] 5.2 Move "新项目" into a separate button wired to `startNewProject`; do not render it as a history option.
- [x] 5.3 Add delete confirmation UI and disable or block deletion for projects whose latest task is still non-terminal.
- [x] 5.4 Add UI for editing the user-level default export directory, including browse/open affordance where consistent with existing directory controls.
- [x] 5.5 Update all managed workflow pages to pass the new history and output settings props without duplicating workflow-specific logic.

## 6. Verification

- [x] 6.1 Run `pytest tests/test_project_workspace.py tests/test_api_app.py tests/test_config_service.py` and fix any regressions.
- [x] 6.2 Run `npm run typecheck` from `frontend/` and fix TypeScript errors.
- [ ] 6.3 Manually verify in the WebUI that task completion refreshes project status, status labels appear before names, the new-project button clears selection, deleting a project removes it from history, and output directories follow the project-level > user-level > fallback priority.

## 7. API Failure Diagnostics And Minimum Output Validation

- [x] 7.1 Replace combined API failure logging with one formatted JSON diagnostic file per failed attempt in a dedicated failure-log directory, with API keys and authorization fields redacted.
- [x] 7.2 Include useful context in each failure file: project/chapter or batch when available, stage, API display name, attempt number, status code, error type, exception summary/traceback, and response content when available.
- [x] 7.3 Add persisted `minimum_output_characters` configuration, with load/save validation and `0` as the disabled value.
- [x] 7.4 Apply minimum output character validation before writing summaries or marking units complete; discard too-short outputs and retry using the existing retry policy.
- [x] 7.5 Add focused tests for per-attempt failure files, secret redaction, formatted JSON readability, disabled minimum length behavior, retry on too-short output, and failure after retry exhaustion.
- [x] 7.6 Commit this feature block after the focused checks pass.

## 8. Project Draft Save Semantics

- [x] 8.1 Rename the WebUI action from "保存名称" to "保存项目".
- [x] 8.2 Refactor managed project editing so project name, chapter files, output directory, and related restorable metadata stay in a local draft until "保存项目" or task start.
- [x] 8.3 Ensure removing chapter files before saving does not delete or update backend saved chapter state.
- [x] 8.4 Auto-save the current project draft before starting a summary task, and block task start with a clear error if the save fails.
- [x] 8.5 Add backend/API tests and frontend tests or documented manual checks for save-project, deferred deletion, and task-start auto-save behavior.
- [x] 8.6 Commit this feature block after the focused checks pass.

## 9. Project Import Status And Output Directory

- [x] 9.1 When importing an existing project directory, save that directory as the project-level custom output directory.
- [x] 9.2 Add immediate imported-project status recognition by scanning available metadata, chapter files, cache files, task state, and generated outputs.
- [x] 9.3 Refresh project details and history after import so recognized status appears before the user starts a task.
- [x] 9.4 Add tests or documented fixtures for importing complete, partial, and unrecognized project directories.
- [x] 9.5 Commit this feature block after the focused checks pass.

## 10. Output Directory Migration

- [x] 10.1 Detect when the current output directory contains generated files before saving a changed output directory.
- [x] 10.2 Prompt the user to choose whether to migrate existing files to the new output directory.
- [x] 10.3 Implement backend migration so metadata updates only after migration succeeds; declining migration preserves old files and saves only the new directory.
- [x] 10.4 Add tests for migrate, decline migration, migration failure, and existing-file detection.
- [x] 10.5 Commit this feature block after the focused checks pass.

## 11. WebUI Polish And Review Follow-up

- [x] 11.1 Adjust the project-name input styling so it has a single-line visual height and cannot be mistaken for a multi-line field.
- [x] 11.2 Review the findings from commit `4e86e0c56a5e87f26925a5630a5b61bc86501319` and, if approved, fix tag extraction/output handling before relying on the new minimum output validation.
- [ ] 11.3 Manually verify in the WebUI that save-project, draft deletion, import status recognition, output migration prompt, and project-name input height behave correctly.
- [x] 11.4 Commit this feature block after the focused checks pass.
