## Purpose
Define the backend task runtime and API surface used by the WebUI to start, observe, control, and resume supported long-running workflows.

## Requirements

### Requirement: Unified Task Model
The backend SHALL represent novel summarization, article summarization, custom summarization, and chapter splitting as managed tasks with a consistent task model.

#### Scenario: Start managed task
- **WHEN** the WebUI requests a supported task with valid parameters
- **THEN** the backend SHALL create a task identifier and return its initial status

### Requirement: Task Status Query
The backend SHALL expose task status including task identifier, type, lifecycle state, progress text, timestamps, and latest result summary.

#### Scenario: Query existing task
- **WHEN** the WebUI queries a known task identifier
- **THEN** the backend SHALL return the latest known status for that task

### Requirement: Task Control Operations
The backend SHALL support pause, resume, and cancel operations for running tasks where the underlying workflow supports them.

#### Scenario: Cancel running task
- **WHEN** the WebUI requests cancellation for a running task
- **THEN** the backend SHALL signal cancellation and eventually move the task to a cancelled or failed terminal state

### Requirement: Realtime Event Stream
The backend SHALL provide a realtime event stream for task logs and progress updates.

#### Scenario: Subscribe to events
- **WHEN** the WebUI subscribes to a task event stream
- **THEN** the backend SHALL emit structured events for logs, progress updates, state changes, warnings, and failures

### Requirement: Resume Existing Work
The task runtime SHALL preserve existing resumability behavior based on the current cache and state files.

#### Scenario: Restart interrupted summarization
- **WHEN** the user starts a summarization task for a folder with existing cache state
- **THEN** the backend SHALL continue from completed stages where the current logic can determine completion

### Requirement: Error Reporting
The task runtime SHALL report recoverable validation errors separately from unexpected execution failures.

#### Scenario: Invalid task request
- **WHEN** the WebUI submits missing or invalid task parameters
- **THEN** the backend SHALL reject the request with actionable validation details and SHALL NOT start a background task

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

### Requirement: Project History API
The backend SHALL expose API operations for listing and loading managed project history.

#### Scenario: List project history
- **WHEN** the WebUI requests historical projects
- **THEN** the backend SHALL return project summaries with project identity, workflow type, uploaded file summary, output target, latest task status, and update timestamp

#### Scenario: Load project details
- **WHEN** the WebUI requests details for a historical project
- **THEN** the backend SHALL return restorable project state including uploaded-file references, output settings, and resumable task context

#### Scenario: Project history unavailable
- **WHEN** a requested historical project does not exist or is missing required metadata
- **THEN** the backend SHALL return a clear validation error and SHALL NOT fabricate project state

### Requirement: Open Directory API
The backend SHALL expose an API for opening managed or custom output directories on the local machine.

#### Scenario: Open valid directory
- **WHEN** the WebUI requests to open a valid output directory
- **THEN** the backend SHALL ask the local operating system to open that directory and return success

#### Scenario: Reject invalid directory
- **WHEN** the WebUI requests to open an invalid or unsafe directory
- **THEN** the backend SHALL return a validation error and SHALL NOT invoke the operating system open action

### Requirement: Accurate Task Terminal State
The task runtime SHALL mark tasks as failed when workflow execution raises an API error or other unexpected exception.

#### Scenario: Workflow execution fails
- **WHEN** a running workflow raises an API error or unexpected exception
- **THEN** the task runtime SHALL move the task to a failed terminal state and SHALL NOT report it as successful completion

### Requirement: API Failure Diagnostics
The task runtime SHALL preserve enough API input and output context to diagnose failures.

#### Scenario: API call fails
- **WHEN** an API call fails during a workflow
- **THEN** the task runtime SHALL log the request context and available response or exception details for troubleshooting
