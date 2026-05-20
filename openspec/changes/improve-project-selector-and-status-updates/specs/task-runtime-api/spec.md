## MODIFIED Requirements

### Requirement: Project History API
The backend SHALL expose API operations for listing, loading, deleting, and managing managed project history.

#### Scenario: List project history
- **WHEN** the WebUI requests historical projects
- **THEN** the backend SHALL return project summaries with project identity, workflow type, uploaded file summary, output target, latest task status, and update timestamp

#### Scenario: Load project details
- **WHEN** the WebUI requests details for a historical project
- **THEN** the backend SHALL return restorable project state including uploaded-file references, output settings, and resumable task context

#### Scenario: Delete project history
- **WHEN** the WebUI requests deletion for a historical project
- **THEN** the backend SHALL delete that managed project and return a success response suitable for refreshing the project list

#### Scenario: Project history unavailable
- **WHEN** a requested historical project does not exist or is missing required metadata
- **THEN** the backend SHALL return a clear validation error and SHALL NOT fabricate project state

### Requirement: Managed Output Targets
The backend task API SHALL accept managed output targets based on project name, optional project-level custom output directory, and user-level default export directory.

#### Scenario: Start workflow with project-level custom output
- **WHEN** a task request includes a valid project-level custom output directory
- **THEN** the backend SHALL validate and use that directory as the task output target

#### Scenario: Start workflow with user-level default output
- **WHEN** a task request omits a project-level custom output directory and a valid user-level default export directory is configured
- **THEN** the backend SHALL resolve the output target under the user-level default export directory for the request's project name

#### Scenario: Start workflow with fallback managed output
- **WHEN** a task request omits a project-level custom output directory and no valid user-level default export directory is configured
- **THEN** the backend SHALL resolve the output target to the current managed fallback export directory for the request's project name
