## ADDED Requirements

### Requirement: Studio Layout Preservation Of Workbench Capabilities
The WebUI workbench SHALL preserve existing workflow capabilities when adopting the studio layout.

#### Scenario: Preserve task controls in studio layout
- **WHEN** a supported long-running task is pending, running, paused, canceling, terminal, or interrupted in the redesigned studio layout
- **THEN** the workbench SHALL show the valid task controls and SHALL disable or hide invalid actions for the current task state

#### Scenario: Preserve live logs in studio layout
- **WHEN** the backend emits global or API-specific task events in the redesigned studio layout
- **THEN** the workbench SHALL keep those logs visible or reachable from the studio feedback area
- **AND** the user SHALL still be able to distinguish global logs from API-specific logs

#### Scenario: Preserve project state in studio layout
- **WHEN** the user switches between workflow views in the redesigned studio layout
- **THEN** unsaved form state, selected project context, uploaded file lists, and recoverable warnings SHALL remain preserved according to the existing workbench behavior

### Requirement: Studio Navigation For Core Workflows
The WebUI workbench SHALL provide studio navigation that keeps all core workflows reachable while exposing richer project context for the active workflow.

#### Scenario: Switch workflow from studio navigation
- **WHEN** the user selects a workflow from the studio navigation
- **THEN** the workbench SHALL display the selected workflow's primary work surface and current-step actions
- **AND** the previous workflow's local draft state SHALL NOT be lost solely because the navigation changed

#### Scenario: Show workflow-specific context index
- **WHEN** a workflow has relevant context such as projects, chapters, reports, prompt nodes, modules, or API profiles
- **THEN** the studio navigation or adjacent context area SHALL provide a readable index for that context when data is available

### Requirement: Studio Stage And Feedback Surfaces
The WebUI workbench SHALL present progress, logs, warnings, and repair feedback in studio surfaces that remain connected to the active project or task.

#### Scenario: Show stage flow for summary project
- **WHEN** the user opens a novel summary project with live or persisted stage progress
- **THEN** the redesigned page SHALL show a stage flow or equivalent progress surface for small summary, big summary, super summary, and final summary stages

#### Scenario: Show feedback near affected context
- **WHEN** the WebUI displays upload errors, output directory errors, API configuration warnings, repair warnings, trigger scan warnings, or partial-result warnings
- **THEN** the redesigned layout SHALL show the feedback near the affected project, output, configuration, report, or task context

#### Scenario: Keep terminal states distinct
- **WHEN** the redesigned layout displays `success`, `failed`, `cancelled`, `partial_failed`, or `interrupted`
- **THEN** it SHALL preserve the existing distinct state meanings and SHALL NOT remap them into generic success or failure states

### Requirement: Studio Workflow Page Completeness
The redesigned workbench SHALL keep each existing workflow page functionally complete after visual and layout migration.

#### Scenario: Novel summary page completeness
- **WHEN** the novel summary workflow is migrated to the studio layout
- **THEN** the page SHALL still support project history, project save, source TXT upload, split preview, split-and-ingest, chapter upload/removal, output directory validation, API selection, summary output format, task parameters, word count settings, stage progress, project repair, and task start controls

#### Scenario: Trigger scan page completeness
- **WHEN** the trigger scan workflow is migrated to the studio layout
- **THEN** the page SHALL still support profile management, scan configuration, startup checks, resume report configuration, live findings, report history, report detail views, filters, spoiler controls, review actions, context inspection, notes, export, delete, and warnings

#### Scenario: Supporting pages completeness
- **WHEN** article summary, custom summary, chapter splitting, prompt editing, or API configuration pages are migrated to the studio layout
- **THEN** each page SHALL preserve its existing inputs, actions, validation, warnings, saved state behavior, and result display behavior
