## MODIFIED Requirements

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
