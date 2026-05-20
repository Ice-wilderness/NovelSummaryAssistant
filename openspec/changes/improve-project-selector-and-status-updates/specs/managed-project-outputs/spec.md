## ADDED Requirements

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

## MODIFIED Requirements

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
