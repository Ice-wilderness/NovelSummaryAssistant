## ADDED Requirements

### Requirement: Uploaded File References
The backend task API SHALL accept uploaded-file references for workflows that consume text files.

#### Scenario: Start workflow with uploaded references
- **WHEN** the WebUI starts a workflow with uploaded-file references
- **THEN** the backend SHALL validate the references and resolve them to backend-local files before creating the task

#### Scenario: Reject invalid uploaded reference
- **WHEN** a task request includes an unknown, expired, or inaccessible uploaded-file reference
- **THEN** the backend SHALL return a validation error and SHALL NOT create a task

### Requirement: Managed Output Targets
The backend task API SHALL accept managed output targets based on project name and optional custom output directory.

#### Scenario: Start workflow with managed output
- **WHEN** a task request omits a custom output directory
- **THEN** the backend SHALL resolve the output target to the managed export directory for the request's project name

#### Scenario: Start workflow with custom output
- **WHEN** a task request includes a custom output directory
- **THEN** the backend SHALL validate and use that directory as the task output target

### Requirement: Open Directory API
The backend SHALL expose an API for opening managed or custom output directories on the local machine.

#### Scenario: Open valid directory
- **WHEN** the WebUI requests to open a valid output directory
- **THEN** the backend SHALL ask the local operating system to open that directory and return success

#### Scenario: Reject invalid directory
- **WHEN** the WebUI requests to open an invalid or unsafe directory
- **THEN** the backend SHALL return a validation error and SHALL NOT invoke the operating system open action
