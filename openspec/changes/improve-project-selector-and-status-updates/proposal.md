## Why

The current project history controls require a manual page refresh before completed task status is reflected, which makes the WebUI feel stale after long-running work finishes. Project selection and recovery controls also mix status, project names, new-project creation, and deletion in ways that make common recovery mistakes harder to correct.

## What Changes

- Refresh historical project summaries in the WebUI when a task reaches a terminal state so completed, failed, cancelled, or updated status is visible without reloading the page.
- Present project status as a leading visual label separate from the project name, instead of appending status after long names.
- Move "new project" out of the historical project dropdown and provide it as a dedicated action that clears restored-project context and starts a fresh project flow.
- Add a delete-project action for historical projects, with confirmation and clear handling of the selected/deleted project state.
- Allow users to configure a user-level default export directory, with output resolution priority: project-level custom directory, then user-level custom directory, then the current fallback default export directory.
- Write API failure diagnostics as one formatted JSON file per failed attempt in a dedicated failure-log directory, instead of appending all failures into one JSONL-style log.
- When importing an existing project directory, set that directory as the project-level output directory and detect the imported project's current status immediately.
- Rename "save name" to "save project"; persist project name, chapter files, output directory, and related project metadata only when the user saves, while auto-saving before task start.
- Keep unsaved project edits as a draft in the WebUI so removing chapter files or changing other project fields does not update backend state until "save project" or task start.
- When changing the export directory for a project that already has output files, ask whether to migrate existing output files to the new directory.
- Add a minimum output character setting so too-short API responses are discarded and retried as invalid summary attempts.
- Tighten the project-name input to a single-line visual height.
- Preserve existing project restore behavior for real historical projects.

## Capabilities

### New Capabilities

### Modified Capabilities
- `webui-workbench`: Refine historical project controls so status is shown as a leading label, new-project creation is a separate action, deletion is available, and task completion updates are reflected without page refresh.
- `managed-project-outputs`: Extend historical project management to support deleting an incorrect managed project, removing it from history, resolving default export directories from project-level, user-level, and fallback defaults in priority order, importing project output directories, and migrating existing outputs when requested.
- `task-runtime-api`: Expose the backend operation needed by the WebUI to delete managed project history safely, apply the effective managed output target when starting tasks, write per-attempt API failure diagnostics, and reject too-short API outputs for retry.
- `configuration-management`: Add user-level default export directory and minimum output character configuration with validation and safe fallback behavior.

## Impact

- WebUI project/history selector components and task completion handling.
- Backend project history API/service for delete support.
- Managed project metadata and project output folders for deletion behavior.
- User preferences/configuration storage for the default export directory.
- API retry, failure diagnostic logging, and generated cache/log layout.
- Project import, draft-save, output migration, and task-start auto-save behavior.
- Focused tests for status refresh, selector rendering, new-project action, deletion, output directory priority, draft persistence, import status recognition, output migration, per-failure logs, and minimum output length retry.
- Implementation should commit each approved same-type feature block separately after it passes its focused checks.
