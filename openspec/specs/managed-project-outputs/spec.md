## Purpose
Define managed project output directories, project history, custom output overrides, and local directory opening behavior.
## Requirements
### Requirement: Project-Named Export Directories
The system SHALL provide a default export directory grouped by project name under the effective export root when a workflow produces files.

#### Scenario: Use user-level default export directory
- **WHEN** the user has configured a valid user-level default export directory and starts a workflow without choosing a project-level custom output directory
- **THEN** the backend SHALL write generated files under `<user_default_export_directory>/<project_slug>/<workflow_subdir>/`

#### Scenario: Use fallback export directory
- **WHEN** the user has not configured a valid user-level default export directory and starts a workflow without choosing a project-level custom output directory
- **THEN** the backend SHALL write generated files under `<runtime_base>/exports/<project_slug>/<workflow_subdir>/`

#### Scenario: Sanitize project name
- **WHEN** the user provides a project name
- **THEN** the backend SHALL sanitize it before using it as a directory name and SHALL keep the displayed project name readable in the WebUI

#### Scenario: Derive project name
- **WHEN** the user has not typed a project name before selecting input files
- **THEN** the WebUI SHALL derive a project name from the first uploaded file for single-file workflows or generate a timestamped project name for multi-file workflows

### Requirement: Historical Project Selection
The system SHALL allow users to select previously created managed projects so unfinished work can be restored quickly.

#### Scenario: List historical projects
- **WHEN** the user opens a workflow page with managed project support
- **THEN** the backend SHALL provide historical projects sorted by recent update time, including display name, project slug, workflow type, uploaded file summary, output target, and latest task status

#### Scenario: Restore unfinished project
- **WHEN** the user selects a historical project that has uploaded files and incomplete task state
- **THEN** the WebUI SHALL restore the project name, uploaded file list, output target, and resumable task context needed to continue the project

#### Scenario: Historical project has missing files
- **WHEN** the user selects a historical project whose uploaded files or output directories are missing
- **THEN** the WebUI SHALL show a clear warning and SHALL NOT silently start a task with incomplete project data

### Requirement: Custom Output Directory Override
The system SHALL allow users to use the effective default managed output directory or replace it with one project-level custom output directory value, and SHALL require an explicit user action before falling back from an invalid custom directory to the default output directory.

#### Scenario: Use project-level custom output directory
- **WHEN** the user chooses or types a valid project-level custom output directory
- **THEN** the task request SHALL use that directory for generated files before considering any user-level default export directory

#### Scenario: Use user-level default output directory
- **WHEN** the project has no project-level custom output directory and the user has configured a valid user-level default export directory
- **THEN** the WebUI SHALL prefill the output directory field with the project directory under the user-level default export directory

#### Scenario: Use fallback output directory
- **WHEN** the project has no project-level custom output directory and no valid user-level default export directory exists
- **THEN** the WebUI SHALL prefill the output directory field with the current managed fallback export directory

#### Scenario: Reject invalid custom output directory
- **WHEN** the user saves project metadata or starts a workflow with an invalid project-level custom output directory
- **THEN** the backend SHALL reject the request with a clear validation error
- **AND** the backend SHALL preserve the previous saved output target
- **AND** the backend SHALL NOT silently replace the invalid project-level custom output directory with the effective default managed output directory

#### Scenario: User confirms default output fallback
- **WHEN** a project-level custom output directory has been rejected and the user explicitly chooses to use the default output directory
- **THEN** the next save or task-start request SHALL clear the project-level custom output directory
- **AND** the task request SHALL use the effective default managed output directory

#### Scenario: Load legacy invalid custom output directory
- **WHEN** the backend loads historical or imported project metadata whose saved custom output directory is invalid
- **THEN** the backend SHALL resolve the effective output directory to the current default managed output directory
- **AND** the response SHALL include a warning identifying that the saved custom output directory could not be used

### Requirement: Managed Project Deletion
The system SHALL allow users to delete an incorrect managed project from project history and remove WebUI-managed project files only when those files are proven to be owned by the managed project.

#### Scenario: Delete managed project
- **WHEN** the user deletes an existing managed project
- **THEN** the backend SHALL remove the project metadata directory and uploaded-file storage
- **AND** the backend SHALL remove the managed default export directory only if ownership metadata proves it belongs to that project

#### Scenario: Deleted project absent from history
- **WHEN** the user lists historical projects after deleting a managed project
- **THEN** the deleted project SHALL NOT appear in the historical project list

#### Scenario: Preserve unmanaged custom output
- **WHEN** a deleted project has a custom output directory outside the managed default export directory
- **THEN** the backend SHALL NOT delete the custom output directory

#### Scenario: Preserve output without ownership proof
- **WHEN** a deleted project's output directory lacks matching ownership metadata
- **THEN** the backend SHALL preserve that output directory
- **AND** the response SHALL provide enough information for the WebUI to inform the user that files were kept

#### Scenario: Delete missing project
- **WHEN** the user requests deletion for a project that does not exist
- **THEN** the backend SHALL return a clear validation error and SHALL NOT delete unrelated directories

### Requirement: Managed Output Ownership Metadata
The system SHALL write ownership metadata for output directories it creates and manages so destructive cleanup can be bounded to project-owned paths.

#### Scenario: Create managed output directory
- **WHEN** the backend creates a managed output directory for a project
- **THEN** it SHALL write metadata identifying the project slug, output ownership, and managed directory purpose

#### Scenario: Verify ownership before recursive delete
- **WHEN** the backend is about to recursively delete an output directory as part of project deletion
- **THEN** it SHALL verify that ownership metadata matches the project being deleted

### Requirement: Imported Project Output And Status
The system SHALL treat an imported project directory as the project's output directory and SHALL recognize its current status immediately.

#### Scenario: Set imported directory as project output
- **WHEN** the user imports an existing project directory
- **THEN** the backend SHALL save that directory as the project's project-level custom output directory

#### Scenario: Recognize imported project status
- **WHEN** an existing project directory is imported
- **THEN** the backend SHALL inspect available project metadata, chapter files, cache files, task state, and generated outputs to compute the project's current status before any new task is started

#### Scenario: Return imported project details
- **WHEN** project import succeeds
- **THEN** the backend SHALL return restorable project details including recognized status, chapter file references, and effective output directory

### Requirement: Saved Project Metadata Boundary
The system SHALL persist project edits only through explicit save-project or task-start auto-save operations.

#### Scenario: Save project metadata
- **WHEN** the WebUI saves a project draft
- **THEN** the backend SHALL persist the project name, chapter file references, output directory, workflow type, and related restorable metadata together

#### Scenario: Preserve saved files before save
- **WHEN** a user removes chapter files in the WebUI draft but has not saved the project
- **THEN** the backend SHALL keep the previously saved chapter files and metadata unchanged

#### Scenario: Auto-save project before task start
- **WHEN** a task start request includes unsaved draft project state
- **THEN** the backend SHALL persist that project state before resolving task inputs and output directories

### Requirement: Output Directory Migration
The system SHALL support optional migration of existing generated files when a project's output directory changes.

#### Scenario: Detect existing output files before directory change
- **WHEN** a saved project output directory contains generated files and the user changes the output directory
- **THEN** the backend SHALL expose enough information for the WebUI to prompt whether to migrate the files

#### Scenario: Migrate output files
- **WHEN** the user confirms migration to a new output directory
- **THEN** the backend SHALL move or copy existing generated files to the new directory and then update the project output directory metadata

#### Scenario: Keep old output files
- **WHEN** the user declines migration
- **THEN** the backend SHALL update the project output directory metadata and SHALL leave existing generated files in the previous directory

#### Scenario: Migration failure
- **WHEN** output file migration fails
- **THEN** the backend SHALL return a clear error and SHALL leave the saved project output directory metadata unchanged

### Requirement: Open Output Directory
The system SHALL provide an action to open the current effective output directory for a managed project, bounded to the project output target rather than arbitrary local paths.

#### Scenario: Open effective output directory
- **WHEN** the user clicks the open-directory action for a project with a valid effective output directory
- **THEN** the backend SHALL derive the directory from that project's current effective output target
- **AND** the backend SHALL open only that effective output directory

#### Scenario: Reject non-output directory
- **WHEN** an open-directory request attempts to open a path other than the project's current effective output directory
- **THEN** the backend SHALL reject the request with a clear validation error
- **AND** the backend SHALL NOT open the requested path

#### Scenario: Open directory fails
- **WHEN** the operating system cannot open the project's effective output directory because the directory is missing, the GUI environment is unavailable, or the local opener is unavailable
- **THEN** the backend SHALL return an actionable error that the WebUI can display

### Requirement: Trigger Scan Output Directory
The system SHALL store trigger scan artifacts under the managed project's output directory.

#### Scenario: Resolve trigger scan output directory
- **WHEN** a trigger scan task starts for a managed project
- **THEN** the backend SHALL resolve the scan output directory as `<effective_project_output>/trigger_scan/`

#### Scenario: Create trigger scan output directory
- **WHEN** the scan output directory does not exist
- **THEN** the backend SHALL create it before writing reports, history, or exports

### Requirement: Trigger Scan History Files
The system SHALL keep trigger scan history scoped to the project that produced it.

#### Scenario: Save report history index
- **WHEN** a trigger scan report is saved
- **THEN** the backend SHALL update that project's trigger scan history index

#### Scenario: Load report history from imported project
- **WHEN** the user imports an existing project directory containing trigger scan reports
- **THEN** the backend SHALL detect those reports and expose them in the project's recognized status

### Requirement: Trigger Scan Artifacts On Project Deletion
The system SHALL handle trigger scan artifacts consistently with other managed outputs when a project is deleted, using the same ownership boundary as the parent output directory.

#### Scenario: Delete managed trigger scan output
- **WHEN** the user deletes a managed project whose trigger scan output is under an output directory with matching ownership metadata
- **THEN** the backend SHALL remove the trigger scan artifacts with the rest of that managed output directory

#### Scenario: Preserve unmanaged trigger scan output
- **WHEN** the user deletes a project whose custom output directory is outside the managed default export directory
- **THEN** the backend SHALL NOT delete that custom output directory or its trigger scan artifacts

#### Scenario: Preserve trigger scan output without ownership proof
- **WHEN** the user deletes a project whose trigger scan output exists under a directory without matching ownership metadata
- **THEN** the backend SHALL preserve those trigger scan artifacts

### Requirement: Migration Status Recognition
The system SHALL include chapter granularity and trigger scan artifacts in project status recognition.

#### Scenario: Recognize single-chapter project
- **WHEN** an imported or historical project contains single-chapter files
- **THEN** the backend SHALL report that trigger scanning can use precise mode if other required scan configuration is supplied

#### Scenario: Recognize legacy grouped project
- **WHEN** an imported or historical project contains grouped chapter files
- **THEN** the backend SHALL report that migration is required before trigger scanning

### Requirement: Project State Output Reconciliation
The system SHALL reconcile managed project state records, persisted task summaries, intermediate artifacts, and expected output files before presenting a historical or imported project's current status.

#### Scenario: Reconcile project on history load
- **WHEN** the backend lists managed project history
- **THEN** each returned project summary SHALL include a reconciliation status derived from the latest readable project metadata, persisted task summary, intermediate artifacts, and expected output files
- **AND** unreadable or missing optional reconciliation inputs SHALL be reported as project warnings instead of preventing the history list from loading

#### Scenario: Reconcile project on detail load
- **WHEN** the WebUI loads details for a historical project
- **THEN** the backend SHALL return the project's reconciliation status, reconciliation warnings, expected output checks, and any available repair plan together with the restorable project details

#### Scenario: Reconcile imported project
- **WHEN** an existing project directory is imported
- **THEN** the backend SHALL run the same reconciliation checks used for historical project detail loading before returning the imported project's recognized status

#### Scenario: Completed state with available outputs
- **WHEN** project state or a persisted task summary records a completed or partial result and all required output files for that result are present and readable
- **THEN** the reconciliation status SHALL be `ok`
- **AND** the project SHALL preserve the recorded task terminal state

#### Scenario: Completed state with missing required output
- **WHEN** project state or a persisted task summary records a completed or partial result but one or more required output files are missing, unreadable, or inconsistent with the saved output format
- **THEN** the reconciliation status SHALL be `abnormal_completed`
- **AND** the response SHALL include warnings that identify the missing or inconsistent outputs
- **AND** the response SHALL preserve the recorded task terminal state instead of remapping it to incomplete or failed

#### Scenario: Output exists without reliable completed state
- **WHEN** expected generated outputs exist but project state and persisted task summaries do not contain a reliable completed or partial terminal state
- **THEN** the reconciliation status SHALL include a warning that state metadata is incomplete
- **AND** the backend SHALL NOT silently mark the project as normally completed without recording that warning

#### Scenario: Project has no completed state and no generated output
- **WHEN** project state has no reliable completed or partial terminal state and expected generated outputs are absent
- **THEN** the reconciliation status SHALL be incomplete rather than `abnormal_completed`

### Requirement: Project Output Repair Plan
The system SHALL produce a repair plan for reconciled projects when missing or inconsistent outputs can potentially be restored from available inputs, intermediate artifacts, or a user-confirmed rerun.

#### Scenario: Generate repair plan for abnormal completed project
- **WHEN** reconciliation classifies a project as `abnormal_completed`
- **THEN** the backend SHALL return a repair plan containing available repair actions, blocked actions, required inputs, output effects, whether an action may call an LLM API, and whether an action may overwrite existing files

#### Scenario: Repair metadata without LLM
- **WHEN** generated outputs are present but project metadata, progress summaries, history indexes, output path bindings, or imported cache locations are incomplete or stale
- **THEN** the repair plan MAY include an action that corrects only those derived records or path bindings
- **AND** that action SHALL NOT call an LLM API or generate new summary text

#### Scenario: Summary content repair requires LLM disclosure
- **WHEN** a repair action would create or replace missing small-summary, big-summary, super-summary, ultimate-summary, article-summary, or custom-summary text
- **THEN** the repair plan SHALL mark that action as requiring an LLM API call
- **AND** the repair plan SHALL disclose that regenerated summary content may differ from the original run

#### Scenario: Repair by rerunning missing stages
- **WHEN** one or more intermediate artifacts are missing but source files, chapter files, saved settings, and required API configuration are available
- **THEN** the repair plan SHALL include an action to rerun only the missing stages that can be safely identified
- **AND** the action SHALL disclose that outputs may differ from the original run because LLM calls are required

#### Scenario: Block unsafe repair
- **WHEN** required source files, chapter files, saved settings, or API configuration needed for a repair action are missing or unreadable
- **THEN** the repair plan SHALL mark that action as blocked with a user-readable reason
- **AND** the backend SHALL NOT fabricate missing inputs or silently fall back to a broader rerun

#### Scenario: Preserve existing outputs by default
- **WHEN** a repair action would write a path that already contains a generated output file
- **THEN** the repair plan SHALL mark the action as requiring overwrite confirmation or SHALL choose a non-conflicting output path
- **AND** the system SHALL NOT overwrite existing output files as part of reconciliation alone

#### Scenario: No silent repair
- **WHEN** reconciliation detects missing or inconsistent outputs
- **THEN** the backend SHALL NOT rebuild files, rerun workflow stages, or call an LLM API until the user explicitly starts a repair action
