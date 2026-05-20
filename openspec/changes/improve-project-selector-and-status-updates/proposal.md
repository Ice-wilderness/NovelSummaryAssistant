## Why

The current project history controls require a manual page refresh before completed task status is reflected, which makes the WebUI feel stale after long-running work finishes. Project selection and recovery controls also mix status, project names, new-project creation, and deletion in ways that make common recovery mistakes harder to correct.

## What Changes

- Refresh historical project summaries in the WebUI when a task reaches a terminal state so completed, failed, cancelled, or updated status is visible without reloading the page.
- Present project status as a leading visual label separate from the project name, instead of appending status after long names.
- Move "new project" out of the historical project dropdown and provide it as a dedicated action that clears restored-project context and starts a fresh project flow.
- Add a delete-project action for historical projects, with confirmation and clear handling of the selected/deleted project state.
- Allow users to configure a user-level default export directory, with output resolution priority: project-level custom directory, then user-level custom directory, then the current fallback default export directory.
- Preserve existing project restore behavior for real historical projects.

## Capabilities

### New Capabilities

### Modified Capabilities
- `webui-workbench`: Refine historical project controls so status is shown as a leading label, new-project creation is a separate action, deletion is available, and task completion updates are reflected without page refresh.
- `managed-project-outputs`: Extend historical project management to support deleting an incorrect managed project, removing it from history, and resolving default export directories from project-level, user-level, and fallback defaults in priority order.
- `task-runtime-api`: Expose the backend operation needed by the WebUI to delete managed project history safely and apply the effective managed output target when starting tasks.
- `configuration-management`: Add user-level default export directory configuration with validation and safe fallback behavior.

## Impact

- WebUI project/history selector components and task completion handling.
- Backend project history API/service for delete support.
- Managed project metadata and project output folders for deletion behavior.
- User preferences/configuration storage for the default export directory.
- Focused tests for status refresh, selector rendering, new-project action, deletion, and output directory priority.
