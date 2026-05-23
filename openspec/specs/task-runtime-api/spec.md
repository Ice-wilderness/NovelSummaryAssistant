## Purpose
Define the backend task runtime and API surface used by the WebUI to start, observe, control, and resume supported long-running workflows.
## Requirements
### Requirement: Unified Task Model
The backend SHALL represent novel summarization, article summarization, custom summarization, chapter splitting, trigger scanning, small-summary-only preparation, and model fetching as managed tasks with a consistent task model.

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
The backend task runtime SHALL write one readable diagnostic file for each failed API attempt.

#### Scenario: Log failed API attempt
- **WHEN** an API attempt fails due to request error, HTTP error, response parsing error, invalid response shape, or minimum output length validation
- **THEN** the backend SHALL write a single formatted JSON diagnostic file for that failed attempt in a dedicated API failure-log directory

#### Scenario: Avoid combined failure log
- **WHEN** multiple API attempts fail during a task
- **THEN** the backend SHALL create separate formatted JSON files for each failure instead of appending all failures into one JSONL-style file

#### Scenario: Redact sensitive diagnostic fields
- **WHEN** the backend writes an API failure diagnostic file
- **THEN** the file SHALL omit or redact API keys, authorization headers, and other secret credentials

#### Scenario: Include useful diagnostic context
- **WHEN** the backend writes an API failure diagnostic file
- **THEN** the file SHALL include task stage, project or chapter context when available, API display name, attempt number, error type, status code when available, traceback or error summary, and response content when available

### Requirement: Minimum Output Length Validation
The backend task runtime SHALL reject API outputs whose visible content is shorter than the configured minimum output character count.

#### Scenario: Accept output meeting minimum length
- **WHEN** the configured minimum output character count is zero or the API output visible content length is greater than or equal to the configured value
- **THEN** the backend SHALL accept the output for the normal task pipeline

#### Scenario: Reject output below minimum length
- **WHEN** the API output visible content length is below the configured minimum output character count
- **THEN** the backend SHALL discard the output, write an API failure diagnostic file, and retry according to the existing retry policy

#### Scenario: Exhaust retries after short outputs
- **WHEN** all retry attempts produce output below the configured minimum output character count
- **THEN** the backend SHALL fail that unit with a clear error and SHALL NOT write the too-short output as a completed summary

### Requirement: Trigger Scan Task API
The backend task API SHALL expose operations needed to validate, start, observe, cancel, and resume trigger scan tasks.

#### Scenario: Validate trigger scan request
- **WHEN** the WebUI submits trigger scan configuration for startup checks
- **THEN** the backend SHALL return whether the request is ready to start or which user decisions are required

#### Scenario: Start trigger scan
- **WHEN** startup checks pass and the WebUI starts a trigger scan
- **THEN** the backend SHALL create a `trigger_scan` task using the unified task runtime

#### Scenario: Query trigger scan task
- **WHEN** the WebUI queries a running trigger scan task
- **THEN** the backend SHALL return task status, lifecycle state, progress text, timestamps, latest result summary, and scan-specific progress metadata when available

### Requirement: Structured Trigger Scan Events
The backend task runtime SHALL stream structured events for trigger scan progress and intermediate results.

#### Scenario: Stream scan progress event
- **WHEN** a scan stage or chapter progresses
- **THEN** the backend SHALL emit an event containing stage name, completed count, total count, and progress text

#### Scenario: Stream intermediate result event
- **WHEN** a chapter produces findings before the scan completes
- **THEN** the backend SHALL emit an event containing enough finding summary data for the WebUI to append it to the current result list

### Requirement: Small Summary Only Task Mode
The backend task API SHALL support running only the small-summary stage for a novel project.

#### Scenario: Start small-summary-only task
- **WHEN** the WebUI requests small-summary-only preparation for a valid novel project
- **THEN** the backend SHALL start a managed task that stops after small summaries are complete

#### Scenario: Reject unsupported small-summary-only request
- **WHEN** the request does not identify a valid novel project with chapter files
- **THEN** the backend SHALL return a validation error and SHALL NOT start a task
