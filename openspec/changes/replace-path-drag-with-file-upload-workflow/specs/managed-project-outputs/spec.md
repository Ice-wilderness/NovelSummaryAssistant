## ADDED Requirements

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

### Requirement: Custom Output Directory Override
The system SHALL allow users to choose a custom output directory instead of the managed default export directory.

#### Scenario: Choose custom output directory
- **WHEN** the user chooses a custom output directory with the browse button
- **THEN** the task request SHALL use that directory for generated files instead of the managed default export directory

#### Scenario: Clear custom output directory
- **WHEN** the user clears the custom output directory selection
- **THEN** the workflow SHALL return to the managed default export directory for subsequent task starts

### Requirement: Open Output Directory
The system SHALL provide an action to open generated output directories from the WebUI.

#### Scenario: Open managed output directory
- **WHEN** the user clicks the open-directory action for a managed project export directory
- **THEN** the backend SHALL ensure the directory exists and request the local operating system to open it

#### Scenario: Open custom output directory
- **WHEN** the user clicks the open-directory action for a custom output directory
- **THEN** the backend SHALL validate the directory and request the local operating system to open it or return a clear error

#### Scenario: Open directory fails
- **WHEN** the operating system cannot open the requested directory
- **THEN** the backend SHALL return an actionable error that the WebUI can display
