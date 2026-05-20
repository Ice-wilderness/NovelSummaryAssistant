## Purpose
Define managed project output directories, project history, custom output overrides, and local directory opening behavior.

## Requirements

### Requirement: Project-Named Export Directories
The system SHALL provide a default export directory grouped by project name when a workflow produces files.

#### Scenario: Use default export directory
- **WHEN** the user starts a workflow without choosing a custom output directory
- **THEN** the backend SHALL write generated files under `<runtime_base>/exports/<project_slug>/`

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
The system SHALL allow users to use the default managed output directory or replace it with one custom output directory value.

#### Scenario: Use default output directory
- **WHEN** the user opens a managed workflow without a custom output directory
- **THEN** the WebUI SHALL prefill the output directory field with the managed default export directory

#### Scenario: Choose custom output directory
- **WHEN** the user chooses or types a valid custom output directory
- **THEN** the task request SHALL use that directory for generated files instead of the managed default export directory

#### Scenario: Reject invalid custom output directory
- **WHEN** the user enters an invalid custom output directory
- **THEN** the WebUI SHALL return the output directory field to the managed default export directory

### Requirement: Open Output Directory
The system SHALL provide an action to open generated output directories from the WebUI.

#### Scenario: Open effective output directory
- **WHEN** the user clicks the open-directory action
- **THEN** the backend SHALL open the output directory currently used by the project, whether it is managed or custom

#### Scenario: Open directory fails
- **WHEN** the operating system cannot open the requested directory
- **THEN** the backend SHALL return an actionable error that the WebUI can display
