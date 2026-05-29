## 1. Design Foundation

- [x] 1.1 Audit current WebUI screens and map every existing workflow capability to the new studio layout regions.
- [x] 1.2 Select and document any new frontend dependencies for animation, accessible primitives, tooltips, dialogs, scroll areas, or styling helpers.
- [x] 1.3 Add approved frontend dependencies and verify the frontend still installs, typechecks, and builds.
- [x] 1.4 Create the studio design foundation with shared tokens, layout primitives, panel/card styles, focus states, status treatments, and motion utilities.
- [x] 1.5 Add a PC desktop visual verification target or script/process for checking redesigned pages at desktop-width viewport.

## 2. Studio Workbench Shell

- [ ] 2.1 Implement the Studio shell layout with top task status, workflow navigation, primary work surface, current-step inspector, and live feedback/log region.
- [ ] 2.2 Migrate workflow navigation into the Studio shell while preserving active view switching and per-view draft state.
- [ ] 2.3 Rework shared task controls for the Studio top/status area and preserve valid/invalid control behavior for running, paused, cancelled, failed, partial, interrupted, and idle states.
- [ ] 2.4 Rework live logs into a Studio feedback surface with global/API source switching and expandable long messages.
- [ ] 2.5 Rework stage progress into a Studio stage-flow surface using existing task and project progress data.

## 3. Novel Summary Studio Page

- [ ] 3.1 Redesign the novel summary page around project context, source manuscript upload, split preview, chapter list, output target, and current next actions.
- [ ] 3.2 Preserve project history, save project, start new project, import project, delete project, and project draft behavior in the new layout.
- [ ] 3.3 Preserve source TXT upload, split mode selection, pattern/title-list options, split preview, split-and-ingest, and manual chapter upload/removal.
- [ ] 3.4 Preserve output directory validation, open-directory action, default fallback action, and migration confirmation behavior.
- [ ] 3.5 Preserve API selection, final summary API, summary output format, flow mode, batch settings, threshold settings, and word count settings in a more comfortable task recipe layout.
- [ ] 3.6 Preserve project repair warnings/actions and required confirmations for LLM, content-changing, or overwrite repairs.
- [ ] 3.7 Add motion and visual feedback for upload, split preview, task start, stage progress, repair warnings, and terminal states.
- [ ] 3.8 Update novel summary tests for the redesigned accessible structure and run the relevant frontend tests.

## 4. Trigger Scan Studio Page

- [ ] 4.1 Redesign trigger scan around project/report context, scan configuration, profile management, live findings, and current review actions.
- [ ] 4.2 Preserve profile create, duplicate, delete, import, export, group/rule editing, dirty state, expand/collapse, and save behavior.
- [ ] 4.3 Preserve scan project selection, report resume selection, scan range, scan API selection, verification settings, confidence settings, batch settings, quote limit, skip advice, minimum output characters, precheck, save config, start, resume, and cancel behavior.
- [ ] 4.4 Preserve report history, report loading, event/finding views, filters, pagination, spoiler controls, review status actions, notes, context modal, export, delete, warnings, and legacy/partial status display.
- [ ] 4.5 Add polished transitions and feedback for tab switching, precheck decisions, live findings, filter changes, context inspection, review actions, and exports.
- [ ] 4.6 Update trigger scan tests for the redesigned accessible structure and run the relevant frontend tests.

## 5. Supporting Workflow Pages

- [ ] 5.1 Migrate article summary and custom summary pages into the Studio layout while preserving input, task start, result, warning, partial-failure, and terminal-state behavior.
- [ ] 5.2 Migrate chapter splitting page into the Studio layout while preserving source selection, pattern configuration, preview, output controls, task start, and error display.
- [ ] 5.3 Migrate prompt editor page into the Studio layout while preserving workflow selection, prompt node editing, module editing, unsaved state, and save behavior.
- [ ] 5.4 Migrate API configuration page into the Studio layout while preserving config recovery warnings, model list behavior, secret handling, enable/disable state, and save behavior.
- [ ] 5.5 Add page-specific motion and visual polish that supports each workflow without hiding validation, warnings, or destructive confirmations.

## 6. Verification And Cleanup

- [ ] 6.1 Run frontend typecheck and build after all migrated pages compile.
- [ ] 6.2 Run the relevant frontend test suite and update tests only for intentional accessible structure changes.
- [ ] 6.3 Perform PC desktop visual checks for key states: empty project, loaded project, running task, terminal task, repair warning, trigger scan report review, and log-heavy session.
- [ ] 6.4 Verify no existing workflow capability listed in the specs was lost during migration.
- [ ] 6.5 Remove obsolete layout CSS, unused components, and transitional compatibility code introduced during migration.
- [ ] 6.6 Update documentation or inline developer notes for new Studio layout primitives, dependency purpose, and visual verification workflow.
