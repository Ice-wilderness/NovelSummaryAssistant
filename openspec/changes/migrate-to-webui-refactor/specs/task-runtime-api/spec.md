## ADDED Requirements

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
