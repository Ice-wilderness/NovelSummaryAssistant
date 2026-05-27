## 1. Reconciliation Model And Backend Checks

- [x] 1.1 Add backend data models for reconciliation status, output checks, reconciliation warnings, repair plans, and repair actions.
- [x] 1.2 Add a focused project reconciliation service under `webui_backend/workspace_services/` that reads project metadata, persisted task summaries, low-level progress state, intermediate artifacts, and expected output files without mutating them.
- [x] 1.3 Implement lightweight history-list reconciliation that returns project-level status and primary warnings without doing expensive full scans.
- [x] 1.4 Implement full project-detail reconciliation for historical project load and import flows.
- [x] 1.5 Classify completed or partial records with missing, unreadable, or format-inconsistent required outputs as `abnormal_completed` while preserving the original terminal task status.
- [x] 1.6 Classify projects with outputs but incomplete metadata separately from ordinary incomplete projects.

## 2. Repair Plan Generation

- [x] 2.1 Generate repair plans for abnormal completed novel summary projects, including action id, availability, blocked reason, required inputs, affected outputs, repair kind, LLM requirement, overwrite requirement, and content-variance disclosure.
- [x] 2.2 Add no-LLM repair actions only for metadata, progress summary, history index, output path binding, or imported cache-location correction.
- [x] 2.3 Add LLM repair actions for rerunning identifiable missing summary stages when source files, chapter files, saved settings, and API configuration are available.
- [x] 2.4 Mark repair actions as blocked when required source files, chapter files, settings, API configuration, or workflow support are missing.
- [x] 2.5 Ensure workflows without first-round repair support return an unsupported or blocked repair plan instead of pretending repair is available.

## 3. Repair Task API And Execution

- [x] 3.1 Add API types and routes for fetching the latest repair plan and starting a selected repair action.
- [x] 3.2 Recompute or validate the repair plan when a repair start request arrives, and reject stale action ids.
- [x] 3.3 Reject repair start requests that need LLM calls, content regeneration, or overwrite unless the request includes explicit confirmation flags.
- [x] 3.4 Run project repair as a separate managed task associated with the same project, preserving original task history.
- [x] 3.5 Implement no-LLM metadata/index/path repair without generating or rewriting summary text.
- [x] 3.6 Implement missing-stage LLM rerun repair for the safe novel summary cases identified by the repair plan.
- [x] 3.7 Refresh and persist project reconciliation data after repair task terminal states.

## 4. WebUI Status And Repair Controls

- [x] 4.1 Extend frontend API types and display helpers for reconciliation status, output checks, warnings, and repair plans.
- [x] 4.2 Show `abnormal_completed` distinctly in project history without rewriting the historical task status.
- [x] 4.3 Show project-detail warnings explaining missing or inconsistent outputs and the difference between abnormal completion and ordinary incomplete work.
- [x] 4.4 Render available and blocked repair actions from backend-provided repair plans.
- [x] 4.5 Add confirmation flow for repair actions that may call an LLM, change generated content, or overwrite existing files.
- [x] 4.6 Start repair tasks from the selected action id and display progress through the existing task status/event surfaces.
- [x] 4.7 Refresh project details and history after repair task completion, partial failure, failure, or cancellation.

## 5. Tests And Verification

- [x] 5.1 Add backend tests for history-list and detail reconciliation across normal completion, abnormal completion, ordinary incomplete, metadata-incomplete, and unreadable metadata cases.
- [x] 5.2 Add backend tests for repair plan generation, including no-LLM metadata/index/path repair, LLM missing-stage rerun, blocked inputs, unsupported workflows, LLM disclosure, content-variance disclosure, and overwrite disclosure.
- [x] 5.3 Add API tests for repair plan fetch, repair task start, stale plan rejection, blocked action rejection, missing confirmation rejection, and task status updates.
- [x] 5.4 Add workflow service tests for successful repair, partial repair, failed repair without usable output, and preservation of original task history.
- [x] 5.5 Add frontend focused tests for abnormal-completed history display, project-detail warnings, repair plan rendering, confirmation prompts, validation errors, and refresh after repair terminal state.
- [x] 5.6 Run the focused Python tests first, then the relevant frontend tests, then broader `python -m pytest` and frontend build/type checks if the change scope warrants it.

## 6. Documentation And Backlog Sync

- [x] 6.1 Update stability audit follow-up docs to mark state/output reconciliation and repair support according to the implemented scope.
- [x] 6.2 Document the product distinction between task lifecycle status, project reconciliation status, abnormal completion, ordinary incomplete work, and user-triggered repair.
- [x] 6.3 Record verification commands and any intentionally unsupported workflows in the change notes or related maintenance docs.
