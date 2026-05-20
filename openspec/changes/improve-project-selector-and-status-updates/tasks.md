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
