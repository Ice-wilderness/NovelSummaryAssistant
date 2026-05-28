## Purpose
Define the browser-based workbench that replaces the legacy desktop GUI as the primary interface for workflows, logs, controls, responsiveness, and project attribution.
## Requirements
### Requirement: Local WebUI Entry
The system SHALL provide a local browser-based workbench as the primary user interface for the application.

#### Scenario: Open workbench
- **WHEN** the user starts the WebUI entry command
- **THEN** the system SHALL start a local server and expose a browser-accessible workbench URL

#### Scenario: Existing desktop entry is not primary
- **WHEN** the user uses the legacy desktop entry after migration
- **THEN** the system SHALL either launch the WebUI workflow or clearly indicate how to open the WebUI

### Requirement: Core Workflow Navigation
The WebUI workbench SHALL provide navigable views for novel summarization, article summarization, custom summarization, chapter splitting, trigger scanning, prompt editing, API configuration, and logs.

#### Scenario: Switch workflow
- **WHEN** the user selects a workflow view
- **THEN** the workbench SHALL display the controls and status relevant to that workflow without losing unsaved form state in other views

#### Scenario: Open trigger scanning view
- **WHEN** the user selects the trigger scanning navigation item
- **THEN** the workbench SHALL display trigger profile management, scan configuration, and scan results tabs

### Requirement: Page Guidance
The WebUI workbench SHALL provide concise guidance for every current page so users can understand each workflow, button, configuration item, and module without leaving the page.

#### Scenario: View page guidance
- **WHEN** the user opens any primary workbench page
- **THEN** the page SHALL include concise guidance explaining the page purpose and the meaning of its main controls

#### Scenario: View field guidance
- **WHEN** the user views a configuration field whose meaning affects task behavior
- **THEN** the field SHALL provide a short label, hint, tooltip, or nearby help text explaining its purpose

#### Scenario: View action guidance
- **WHEN** the user hovers, focuses, or reads a button that starts, saves, resets, deletes, loads, pauses, resumes, or cancels work
- **THEN** the action SHALL be named or described clearly enough to communicate its effect

### Requirement: Prompt Editor Workbench
The WebUI workbench SHALL make the prompt editor usable for workflow-level prompt composition.

#### Scenario: Navigate prompt editor sections
- **WHEN** the user opens the prompt editor
- **THEN** the workbench SHALL provide a clear way to move between workflow selection, prompt node editing, message editing, and module management

#### Scenario: Understand prompt modules
- **WHEN** the user views prompt modules
- **THEN** the workbench SHALL explain where modules can be used and whether changes affect referenced prompt nodes

#### Scenario: Track unsaved prompt edits
- **WHEN** the user changes prompt node messages or modules without saving
- **THEN** the workbench SHALL show an unsaved state and SHALL prevent the change from being mistaken for an active saved configuration

### Requirement: Task Control Surface
The WebUI workbench SHALL allow the user to start, pause, resume, and cancel supported long-running tasks from the browser.

#### Scenario: Control running task
- **WHEN** a supported task is running
- **THEN** the workbench SHALL show available task controls and SHALL disable actions that are invalid for the current task state

### Requirement: Live Logs And Progress
The WebUI workbench SHALL show live global logs, task progress, and API-specific logs while a task is running.

#### Scenario: Receive task log
- **WHEN** the backend emits a task log event
- **THEN** the workbench SHALL append it to the global log view and SHALL route API-specific events to the corresponding API log view

#### Scenario: Display stage progress bar
- **WHEN** the user is on a novel summary or trigger scan page with a project loaded
- **THEN** the workbench SHALL display a stage progress bar that covers all workflow stages
- **AND** the progress bar SHALL show the current stage, completed stages, and pending stages with distinct visual treatment
- **AND** the progress bar SHALL update in real time when a task is running

#### Scenario: Show current stage remaining
- **WHEN** a task is running
- **THEN** the progress bar SHALL display how many items remain in the current stage as a completed/total count

#### Scenario: Show overall workflow progress
- **WHEN** the user views the progress bar
- **THEN** the workbench SHALL enable the user to understand at a glance which stage is executing and how many stages have been completed and how many remain

### Requirement: Stage Progress On Project Entry
The WebUI workbench SHALL display stage progress immediately when entering a project, based on available file-system and cache state.

#### Scenario: Enter project with completed stages
- **WHEN** the user selects a historical project that has completed summary stages
- **THEN** the workbench SHALL immediately show which stages are completed, which stage was in progress, and which stages are pending

#### Scenario: Enter project with trigger scan results
- **WHEN** the user selects a historical project that has trigger scan results
- **THEN** the workbench SHALL show trigger scan stage progress alongside summary stage progress when relevant

### Requirement: Modern Responsive Layout
The WebUI workbench SHALL use a modern responsive layout that remains usable on common desktop and tablet browser widths.

#### Scenario: Resize browser
- **WHEN** the browser viewport changes between desktop and tablet widths
- **THEN** the workbench SHALL keep primary navigation, forms, task controls, and logs visible or reachable without overlapping content

#### Scenario: Resize guided page
- **WHEN** the browser viewport changes between desktop and tablet widths
- **THEN** guidance text, form controls, prompt messages, module lists, task controls, and logs SHALL remain visible or reachable without overlapping content

### Requirement: Project Attribution
The WebUI workbench SHALL display project attribution for the original author and current author.

#### Scenario: View attribution
- **WHEN** the user opens the workbench attribution area or project information view
- **THEN** the workbench SHALL show original author `zhoufei_1314` and current author `Ice_wilderness`

### Requirement: Upload-Based Workflow Controls
The WebUI workbench SHALL present upload controls for workflow file inputs and managed output controls for generated files.

#### Scenario: Upload files on workflow page
- **WHEN** the user opens a workflow that consumes local text files
- **THEN** the page SHALL provide file upload controls with accepted file guidance instead of requiring the user to drag or type local file paths

#### Scenario: Configure project output
- **WHEN** the user opens a workflow that produces files
- **THEN** the page SHALL show the project name, effective output directory, browse action, and open-directory action clearly enough to understand where files will be written

#### Scenario: Display effective output priority
- **WHEN** the workflow page displays an output directory for a managed project
- **THEN** the displayed directory SHALL reflect the priority of project-level custom directory, user-level default export directory, then current fallback default export directory

#### Scenario: Display uploaded file list
- **WHEN** the user selects or uploads files
- **THEN** the page SHALL display the uploaded file names and allow removing files before task start

### Requirement: Readable API Client Error Handling
The WebUI API client SHALL preserve HTTP status information and provide readable error details for both JSON and non-JSON failed responses.

#### Scenario: Failed JSON response
- **WHEN** an API request receives a non-2xx response with a JSON body containing `detail`
- **THEN** the WebUI API client SHALL throw an `ApiError` with the response status
- **AND** the error message or detail SHALL include the backend-provided detail

#### Scenario: Failed non-JSON response
- **WHEN** an API request receives a non-2xx response with a plain text, HTML, empty, or otherwise non-JSON body
- **THEN** the WebUI API client SHALL throw an `ApiError` with the response status
- **AND** the error message or detail SHALL include the response status text or a short body preview
- **AND** the WebUI API client SHALL NOT expose a raw JSON parsing exception to the page

### Requirement: Historical Project Recovery Controls
The WebUI workbench SHALL provide controls for selecting historical projects, restoring unfinished work, starting a fresh project, deleting incorrect projects, and keeping displayed project status current after task completion.

#### Scenario: Show historical projects
- **WHEN** the user opens a workflow page with historical projects
- **THEN** the page SHALL provide a history control showing recent project names, workflow type, latest task status as a leading visual label, and update time without appending status text after the project name

#### Scenario: Restore selected project
- **WHEN** the user selects a historical project
- **THEN** the page SHALL restore the project name, uploaded file list, output target, and available resume/start controls for that project

#### Scenario: Import project and show recognized status
- **WHEN** the user imports an existing project directory
- **THEN** the page SHALL refresh project details and history so the imported project's recognized status is visible before the user starts a task

#### Scenario: Start new project
- **WHEN** the user activates the new-project action after a historical project has been selected
- **THEN** the page SHALL clear the selected project context and keep upload-first controls ready for a fresh project

#### Scenario: New project outside history selector
- **WHEN** the user opens the historical project control
- **THEN** the new-project action SHALL be presented separately from historical project options

#### Scenario: Refresh project status after task completion
- **WHEN** a task started from a managed project reaches a terminal state
- **THEN** the workflow page SHALL refresh the affected project history and show the latest task status without requiring a browser refresh

#### Scenario: Delete historical project
- **WHEN** the user confirms deletion of a historical project
- **THEN** the page SHALL request project deletion, remove the project from history, and clear the current project context if the deleted project was selected

#### Scenario: No historical projects
- **WHEN** no historical projects exist for the workflow
- **THEN** the page SHALL keep the upload-first workflow usable and SHALL show an unobtrusive empty history state

### Requirement: Project Draft Save Controls
The WebUI workbench SHALL treat project edits as an explicit project draft until the user saves the project or starts a task.

#### Scenario: Save project button
- **WHEN** the page displays the project save action
- **THEN** the action text SHALL be "保存项目" and SHALL save the project name, chapter files, output directory, and related restorable project metadata

#### Scenario: Stage unsaved project edits
- **WHEN** the user edits the project name, changes the output directory, or removes chapter files before saving
- **THEN** the WebUI SHALL update only the local project draft and SHALL NOT immediately persist those changes to backend project metadata

#### Scenario: Auto-save before task start
- **WHEN** the user starts a summary task with unsaved project draft changes
- **THEN** the WebUI SHALL save the project draft first and SHALL start the task only after the save succeeds

#### Scenario: Defer chapter deletion until save
- **WHEN** the user removes a chapter file from the project draft before saving
- **THEN** the backend's saved chapter file state SHALL remain unchanged until the user saves the project or starts the task

#### Scenario: Single-line project name input
- **WHEN** the project name field is displayed
- **THEN** the field SHALL have single-line input height and SHALL NOT visually resemble a multi-line text area

### Requirement: Output Directory Change Confirmation
The WebUI workbench SHALL protect existing generated files when a project output directory changes.

#### Scenario: Prompt before changing output directory with existing files
- **WHEN** the user saves a changed output directory and the previous output directory contains generated files
- **THEN** the WebUI SHALL ask whether to migrate existing files to the new directory before completing the save

#### Scenario: Save changed output directory without migration
- **WHEN** the user declines migration after changing the output directory
- **THEN** the WebUI SHALL save the new output directory while leaving existing files in the previous directory

#### Scenario: Migrate existing output files
- **WHEN** the user confirms migration after changing the output directory
- **THEN** the WebUI SHALL request backend migration and SHALL keep the project metadata unchanged if migration fails

### Requirement: Local Configuration Warning Display
The WebUI workbench SHALL display local configuration recovery warnings in the page or control surface where the user can act on the affected configuration.

#### Scenario: Display API configuration recovery warning
- **WHEN** the API configuration response includes a recovery warning for corrupted API configuration data
- **THEN** the WebUI SHALL display that warning in the API configuration page or API configuration section

#### Scenario: Display user settings recovery warning
- **WHEN** the user settings response includes a recovery warning for corrupted user settings data
- **THEN** the WebUI SHALL display that warning in the user settings page or settings section

#### Scenario: Display chapter pattern recovery warning
- **WHEN** the chapter pattern response includes a recovery warning for corrupted chapter pattern data
- **THEN** the WebUI SHALL display that warning in the chapter pattern or chapter splitting surface that loads those patterns

### Requirement: Output Directory Validation Recovery
The WebUI workbench SHALL make invalid output directory failures recoverable through an explicit user action rather than silently changing the output target.

#### Scenario: Show default fallback action
- **WHEN** saving a project or starting a task fails because the project-level custom output directory is invalid
- **THEN** the WebUI SHALL show the validation error near the output directory control
- **AND** the WebUI SHALL show an action that lets the user switch to the effective default output directory

#### Scenario: Use default output directory after confirmation
- **WHEN** the user chooses the default output directory fallback action after a custom output directory validation failure
- **THEN** the WebUI SHALL clear the project-level custom output directory from the next save or task-start request
- **AND** the WebUI SHALL display the effective default output directory as the output target

#### Scenario: Preserve invalid path for correction
- **WHEN** the backend rejects an invalid project-level custom output directory
- **THEN** the WebUI SHALL keep the invalid path visible for editing until the user changes it or chooses the default fallback action

### Requirement: Local Path Capability Error Display
The WebUI workbench SHALL display local path capability failures at the control that initiated the action.

#### Scenario: Display local picker unavailable error
- **WHEN** a file or directory picker request fails because the local GUI picker is unavailable
- **THEN** the WebUI SHALL display the actionable error near the picker control that initiated the request

#### Scenario: Display open output directory error
- **WHEN** opening the project output directory fails
- **THEN** the WebUI SHALL display the actionable error near the open-directory control

### Requirement: Trigger Scan Workbench
The WebUI workbench SHALL provide a dedicated trigger scan page for managed novel projects.

#### Scenario: Show trigger scan tabs
- **WHEN** the user opens the trigger scan page
- **THEN** the page SHALL provide tabs for profile management, scan configuration, and scan results

#### Scenario: Select project for trigger scan
- **WHEN** the user configures a trigger scan
- **THEN** the page SHALL let the user select an existing managed novel or chapter-split project with readable chapter files

#### Scenario: Show scan configuration controls
- **WHEN** the user configures a scan
- **THEN** the page SHALL show scan range, scan API selection, minimum confidence, low-confidence retention, skip-advice generation, `precise_chapter_batch_size`, `verification_chapter_batch_size`, verification toggle, verification API, and maximum evidence quote length
- **AND** the page SHALL NOT show a scan mode selector or `coarse_summary_batch_size` control

#### Scenario: Run startup checks before scan
- **WHEN** the user clicks start scan
- **THEN** the page SHALL run backend startup checks and present required user decisions before starting the long-running task
- **AND** those decisions SHALL NOT include generating missing small summaries, scanning only summary-covered chapters, or switching from hybrid to precise mode

### Requirement: Novel Summary Workbench Settings
The WebUI workbench SHALL expose novel summary settings that match backend summary workflow defaults.

#### Scenario: Select summary output format
- **WHEN** the user opens the novel summary page
- **THEN** the page SHALL provide a summary output format selector with Markdown and plain text choices
- **AND** the selector SHALL default to Markdown for projects without a saved value

#### Scenario: Restore saved summary output format
- **WHEN** the user opens a project with a saved `summary_output_format`
- **THEN** the page SHALL restore the saved Markdown or plain text selection before starting a summary task

### Requirement: Unified Splitter Task API Usage
The WebUI workbench SHALL start chapter splitter tasks through the shared API client rather than page-local `fetch` error handling.

#### Scenario: Start splitter task from novel source
- **WHEN** the user confirms split-and-ingest from the novel summary page
- **THEN** the page SHALL call the shared splitter task API client method with the existing splitter request payload
- **AND** splitter task errors SHALL be surfaced through the shared API client error model

#### Scenario: Preserve split-and-ingest success behavior
- **WHEN** the splitter task request succeeds
- **THEN** the novel summary page SHALL keep the existing behavior of clearing the source file, refreshing project state, and clearing the split preview

### Requirement: Task Status Recovery And Terminal Display
The WebUI workbench SHALL recover task status after event stream interruptions and display the backend terminal state without remapping cancellation or partial failure to generic failure.

#### Scenario: Refresh task after event stream error
- **WHEN** a task event stream reports an error or disconnects before a terminal event
- **THEN** the WebUI SHALL request the latest task status from the backend
- **AND** the page SHALL update visible task controls and project status from that response

#### Scenario: Display cancelled task
- **WHEN** the backend reports a task state of `cancelled`
- **THEN** the WebUI SHALL display the task as cancelled rather than failed or completed

#### Scenario: Display partial failed scan
- **WHEN** a trigger scan report or task summary reports `partial_failed`
- **THEN** the WebUI SHALL display the partial failure state and preserve access to available findings, events, and warnings

### Requirement: Summary Partial Warning Display
The WebUI workbench SHALL display article summary and custom summary `partial_failed` states as partial results with usable output and warnings, not as complete success or generic failure.

#### Scenario: Display partial article summary
- **WHEN** an article summary task finishes with status `partial_failed`
- **THEN** the article summary page SHALL show a partial failure state
- **AND** the page SHALL show that the generated final summary is available but may be incomplete
- **AND** the page SHALL show the failed section details returned by the backend

#### Scenario: Display partial custom summary
- **WHEN** a custom summary task finishes with status `partial_failed`
- **THEN** the custom summary page SHALL show a partial failure state
- **AND** the page SHALL keep the generated custom summary output visible
- **AND** the page SHALL show the failed source-file details returned by the backend

#### Scenario: Display summary partial status in shared task surfaces
- **WHEN** the global task status area or project history displays an article summary or custom summary task with status `partial_failed`
- **THEN** the WebUI SHALL label it as a partial result
- **AND** the WebUI SHALL NOT remap it to completed, success, failed, or cancelled

#### Scenario: Handle missing summary partial warnings
- **WHEN** a historical summary project has status `partial_failed` but no structured warning details
- **THEN** the WebUI SHALL display a generic partial-result warning
- **AND** the WebUI SHALL NOT fail to render the project page

### Requirement: Trigger Scan Warning Display
The WebUI workbench SHALL display trigger scan warnings that affect report trustworthiness.

#### Scenario: Show unverified finding warning
- **WHEN** a trigger scan report contains an `unverified` warning
- **THEN** the WebUI SHALL show that warning near the report summary or affected result area

#### Scenario: Show deterministic aggregation status
- **WHEN** the user views trigger scan prompt settings or scan result metadata
- **THEN** the WebUI SHALL make clear that current event aggregation is deterministic and not controlled by an LLM aggregation prompt

### Requirement: Interrupted Task Recovery Display
The WebUI workbench SHALL display backend-reported `interrupted` task status as a restart interruption that requires user action, not as normal failure, success, cancellation, or partial failure.

#### Scenario: Display interrupted task in shared status surface
- **WHEN** the backend reports a task status of `interrupted`
- **THEN** the shared task status surface SHALL label the task as interrupted
- **AND** it SHALL show an actionable message explaining that the backend restarted before the task finished and the user may need to restart or continue from project progress

#### Scenario: Disable controls for interrupted task
- **WHEN** the current task has status `interrupted`
- **THEN** the WebUI SHALL NOT show pause, resume, or cancel as valid actions for that task
- **AND** starting a new supported task SHALL remain available when other validation requirements are met

#### Scenario: Display interrupted status in project history
- **WHEN** a historical project reports `latest_task_status` as `interrupted`
- **THEN** the project history control SHALL show a distinct interrupted status label
- **AND** the project name SHALL remain readable without appending ambiguous failure text

### Requirement: Persisted Terminal Task Display
The WebUI workbench SHALL preserve backend terminal task states loaded from persisted summaries.

#### Scenario: Display persisted cancelled task
- **WHEN** a task status query after backend restart returns `cancelled`
- **THEN** the WebUI SHALL display the task as cancelled rather than failed or completed

#### Scenario: Display persisted partial failed task
- **WHEN** a task status query after backend restart returns `partial_failed`
- **THEN** the WebUI SHALL display the task as a partial result
- **AND** it SHALL preserve available warnings and result details returned by the backend

#### Scenario: Display persisted failed task
- **WHEN** a task status query after backend restart returns `failed`
- **THEN** the WebUI SHALL display the task as failed with the backend-provided error or result summary

#### Scenario: Display persisted successful task
- **WHEN** a task status query after backend restart returns `success`
- **THEN** the WebUI SHALL display the task as completed with the backend-provided result summary when available

### Requirement: Reconciled Project Status Display
The WebUI workbench SHALL display project reconciliation status distinctly from task lifecycle status when historical or imported project outputs are missing or inconsistent.

#### Scenario: Display abnormal completed project in history
- **WHEN** a historical project summary reports reconciliation status `abnormal_completed`
- **THEN** the history control SHALL show a distinct abnormal-completed label or warning indicator
- **AND** the project name SHALL remain readable without appending ambiguous failure text

#### Scenario: Display abnormal completed project details
- **WHEN** the user selects a project with reconciliation status `abnormal_completed`
- **THEN** the page SHALL show that the project previously completed or partially completed but current outputs are missing or inconsistent
- **AND** the page SHALL show the backend-provided reconciliation warnings near the affected project status or output area

#### Scenario: Do not treat abnormal completed as normal completion
- **WHEN** a selected project has reconciliation status `abnormal_completed`
- **THEN** the WebUI SHALL NOT present missing outputs as available
- **AND** the WebUI SHALL NOT hide the warning merely because the latest task status is `success` or `partial_failed`

#### Scenario: Do not treat abnormal completed as ordinary incomplete
- **WHEN** a selected project has reconciliation status `abnormal_completed`
- **THEN** the WebUI SHALL preserve the historical terminal task status in the task or history surface
- **AND** the page SHALL explain that the current issue is output inconsistency rather than a task that never completed

#### Scenario: Display incomplete state separately
- **WHEN** a selected project has no reliable completed state and no generated output
- **THEN** the WebUI SHALL display the project as incomplete without using the abnormal-completed warning

#### Scenario: Display incomplete metadata warning
- **WHEN** generated output exists but state metadata is incomplete
- **THEN** the WebUI SHALL show a warning that the project state is incomplete and may need review
- **AND** the WebUI SHALL keep available output links or status details visible when they are safe to use

### Requirement: Project Repair Controls
The WebUI workbench SHALL provide repair controls for projects with repairable reconciliation warnings and SHALL require user confirmation before starting repairs that may call an LLM API or overwrite existing outputs.

#### Scenario: Show repair plan
- **WHEN** a selected project response includes a repair plan
- **THEN** the page SHALL show available repair actions, blocked actions, required inputs, and expected output effects using backend-provided descriptions

#### Scenario: Start metadata repair
- **WHEN** the user starts a repair action that only corrects metadata, indexes, output path bindings, or imported cache locations and does not overwrite existing output
- **THEN** the WebUI SHALL call the repair task API with the selected action identifier
- **AND** the page SHALL subscribe to and display the repair task's progress like other managed tasks

#### Scenario: Confirm LLM repair
- **WHEN** the user starts a repair action that may call an LLM API, create or replace summary text, or produce text that differs from the original result
- **THEN** the WebUI SHALL show a confirmation that names the possible cost and output-variance implications before calling the repair task API

#### Scenario: Confirm overwrite repair
- **WHEN** the user starts a repair action that may overwrite an existing generated output
- **THEN** the WebUI SHALL require explicit overwrite confirmation before calling the repair task API

#### Scenario: Show blocked repair
- **WHEN** a repair plan marks an action as blocked
- **THEN** the WebUI SHALL show the blocked reason and SHALL NOT present that blocked action as a runnable primary action

#### Scenario: Refresh project after repair terminal state
- **WHEN** a repair task reaches `success`, `partial_failed`, `failed`, or `cancelled`
- **THEN** the WebUI SHALL refresh the project details and history summary so the latest reconciliation status and warnings are visible

#### Scenario: Repair API validation failure
- **WHEN** the backend rejects a repair start request because the plan is stale, blocked, or missing required confirmation
- **THEN** the WebUI SHALL show the validation message and refresh the repair plan before allowing another repair attempt
