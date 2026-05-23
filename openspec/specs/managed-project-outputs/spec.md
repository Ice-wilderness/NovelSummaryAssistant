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
The system SHALL allow users to use the effective default managed output directory or replace it with one project-level custom output directory value.

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
- **WHEN** the user enters an invalid project-level custom output directory
- **THEN** the WebUI SHALL return the output directory field to the effective default managed output directory

### Requirement: Managed Project Deletion
The system SHALL allow users to delete an incorrect managed project from project history and remove WebUI-managed project files.

#### Scenario: Delete managed project
- **WHEN** the user deletes an existing managed project
- **THEN** the backend SHALL remove the project metadata directory, uploaded-file storage, and managed default export directory for that project

#### Scenario: Deleted project absent from history
- **WHEN** the user lists historical projects after deleting a managed project
- **THEN** the deleted project SHALL NOT appear in the historical project list

#### Scenario: Preserve unmanaged custom output
- **WHEN** a deleted project has a custom output directory outside the managed default export directory
- **THEN** the backend SHALL NOT delete the custom output directory

#### Scenario: Delete missing project
- **WHEN** the user requests deletion for a project that does not exist
- **THEN** the backend SHALL return a clear validation error and SHALL NOT delete unrelated directories

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
The system SHALL provide an action to open generated output directories from the WebUI.

#### Scenario: Open effective output directory
- **WHEN** the user clicks the open-directory action
- **THEN** the backend SHALL open the output directory currently used by the project, whether it is managed or custom

#### Scenario: Open directory fails
- **WHEN** the operating system cannot open the requested directory
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
The system SHALL handle trigger scan artifacts consistently with other managed outputs when a project is deleted.

#### Scenario: Delete managed trigger scan output
- **WHEN** the user deletes a managed project whose trigger scan output is under the managed export directory
- **THEN** the backend SHALL remove the trigger scan artifacts with the rest of that managed output directory

#### Scenario: Preserve unmanaged trigger scan output
- **WHEN** the user deletes a project whose custom output directory is outside the managed default export directory
- **THEN** the backend SHALL NOT delete that custom output directory or its trigger scan artifacts

### Requirement: Migration Status Recognition
The system SHALL include chapter granularity and trigger scan artifacts in project status recognition.

#### Scenario: Recognize single-chapter project
- **WHEN** an imported or historical project contains single-chapter files
- **THEN** the backend SHALL report that trigger scanning can use precise mode if other required scan configuration is supplied

#### Scenario: Recognize legacy grouped project
- **WHEN** an imported or historical project contains grouped chapter files
- **THEN** the backend SHALL report that migration is required before trigger scanning
