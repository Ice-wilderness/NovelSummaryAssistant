## 1. Runtime Summary Store

- [ ] 1.1 Add an `interrupted` task status and shared helpers for terminal/inactive task status checks.
- [ ] 1.2 Add a task-summary storage path to `TaskRuntime`, with tolerant JSON read/write helpers.
- [ ] 1.3 Persist a lightweight task summary when a task is created and whenever important lifecycle fields change.
- [ ] 1.4 Persist final result fields, warnings, result data, error, and a minimal terminal event when a task reaches `success`, `failed`, `cancelled`, or `partial_failed`.
- [ ] 1.5 Load persisted task summaries during runtime initialization and convert any non-terminal loaded status to `interrupted` with an actionable warning/error.
- [ ] 1.6 Ensure unreadable or invalid summary files are skipped without preventing backend startup.

## 2. API And Project History Integration

- [ ] 2.1 Pass the runtime task-summary storage directory from `create_app` using the current runtime base path.
- [ ] 2.2 Update `/api/tasks`, `/api/tasks/{task_id}`, and task control operations to handle persisted terminal and interrupted records correctly.
- [ ] 2.3 Update `/api/tasks/{task_id}/events` to expose a final state event and close for persisted terminal or interrupted records without full event replay.
- [ ] 2.4 Update active-task blocking checks so interrupted tasks do not block new summary or trigger scan tasks.
- [ ] 2.5 Update project response/history assembly so a project referencing a loaded persisted summary uses that summary status and warning details.
- [ ] 2.6 Preserve existing project progress fallback when a referenced task summary is missing or unreadable.

## 3. WebUI Status Display

- [ ] 3.1 Extend frontend task status typing and normalization to accept `interrupted`.
- [ ] 3.2 Update shared status labels, task summary copy, and global task surfaces to display `interrupted` distinctly.
- [ ] 3.3 Ensure pause/resume/cancel controls are not offered for interrupted tasks.
- [ ] 3.4 Update historical project status labels to display interrupted tasks without rewriting them as failure, success, cancellation, or partial failure.
- [ ] 3.5 Preserve existing display behavior for persisted `success`, `failed`, `cancelled`, and `partial_failed` tasks.

## 4. Tests

- [ ] 4.1 Add focused `TaskRuntime` tests for summary persistence on start, terminal persistence, restart loading, interrupted conversion, and invalid summary tolerance.
- [ ] 4.2 Add API tests for querying persisted terminal tasks, querying interrupted tasks, event stream close behavior, and task controls on inactive records.
- [ ] 4.3 Add project history/API tests for latest task status recovery from persisted summaries and fallback when summaries are missing.
- [ ] 4.4 Add frontend tests for interrupted status labels, shared task surface messaging, disabled controls, and project history display.
- [ ] 4.5 Update existing tests only where required by the new `interrupted` status contract.

## 5. Verification

- [ ] 5.1 Run focused backend tests for task runtime, task routes, and project history.
- [ ] 5.2 Run focused frontend tests for task status display and project history controls.
- [ ] 5.3 Run `python -m pytest`.
- [ ] 5.4 Run `npm run test` and `npm run build` in `frontend/`.
- [ ] 5.5 Run `openspec validate persist-task-terminal-summaries --strict` and `openspec validate --all`.
