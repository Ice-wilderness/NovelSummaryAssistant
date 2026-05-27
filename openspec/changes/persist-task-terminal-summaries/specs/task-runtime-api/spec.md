## ADDED Requirements

### Requirement: Persistent Task Summaries

The backend task runtime SHALL persist lightweight task summaries so task status remains queryable after a backend restart.

#### Scenario: Persist task summary when task starts
- **WHEN** the backend creates a managed task
- **THEN** the task runtime SHALL write a persisted summary containing the task id, task type, lifecycle status, timestamps, progress text, params summary, warnings, result summary, error, and result data fields that are exposed by the task status API

#### Scenario: Persist terminal task summary
- **WHEN** a task reaches `success`, `failed`, `cancelled`, or `partial_failed`
- **THEN** the task runtime SHALL update the persisted summary with the terminal status, finished timestamp, result summary, error, warnings, and result data

#### Scenario: Load summaries after restart
- **WHEN** the backend starts with existing persisted task summaries
- **THEN** the task runtime SHALL load readable summaries into the task status store
- **AND** the `/api/tasks/{task_id}` endpoint SHALL return loaded summaries for known task identifiers

#### Scenario: Ignore unreadable summary
- **WHEN** a persisted task summary is unreadable or invalid
- **THEN** the task runtime SHALL skip that summary without preventing the backend from starting

### Requirement: Interrupted Task State After Restart

The backend task runtime SHALL represent tasks that were non-terminal before backend restart as interrupted rather than failed, completed, or cancelled.

#### Scenario: Mark running task interrupted
- **WHEN** the backend loads a persisted task summary whose status is `pending`, `running`, `paused`, or `canceling`
- **THEN** the task runtime SHALL convert that loaded record to status `interrupted`
- **AND** the task record SHALL include an actionable warning or error explaining that the backend restarted before the task finished and the task cannot be automatically resumed

#### Scenario: Interrupted task is inactive
- **WHEN** a task has status `interrupted`
- **THEN** task control operations SHALL treat the task as inactive
- **AND** the task SHALL NOT block starting a new summary or trigger scan task

#### Scenario: Interrupted task status is preserved
- **WHEN** the WebUI queries an interrupted task by task id
- **THEN** the backend SHALL return `interrupted`
- **AND** the backend SHALL NOT remap the state to `failed`, `success`, `cancelled`, or `partial_failed`

### Requirement: Persisted Task Event Boundary

The backend task event stream SHALL make persisted terminal and interrupted task states observable without promising full historical event replay.

#### Scenario: Subscribe to persisted terminal task
- **WHEN** the WebUI subscribes to events for a task that was loaded from a persisted terminal summary
- **THEN** the backend SHALL emit a terminal state event or otherwise close the stream after making the terminal state observable
- **AND** the backend SHALL NOT be required to replay historical log or progress events for that task

#### Scenario: Subscribe to interrupted task
- **WHEN** the WebUI subscribes to events for an interrupted task
- **THEN** the backend SHALL emit or expose the interrupted state and close the stream
- **AND** the backend SHALL NOT wait indefinitely for in-memory events that can no longer occur

### Requirement: Project History Uses Persisted Task Summaries

The backend project history API SHALL use loaded task summaries when a managed project references a latest task identifier.

#### Scenario: Project references persisted terminal task
- **WHEN** a managed project has `latest_task_id` matching a loaded persisted summary
- **THEN** the project history and project detail responses SHALL use that summary's latest task status
- **AND** terminal states SHALL remain distinguishable as `success`, `failed`, `cancelled`, or `partial_failed`

#### Scenario: Project references interrupted task
- **WHEN** a managed project has `latest_task_id` matching a loaded interrupted task summary
- **THEN** the project history and project detail responses SHALL report the latest task status as `interrupted`
- **AND** the response SHALL preserve enough warning information for the WebUI to tell the user that the task was stopped by backend restart

#### Scenario: Project references missing summary
- **WHEN** a managed project references a latest task id with no readable persisted summary
- **THEN** the backend SHALL continue using existing project progress recognition and metadata fallback behavior
- **AND** the missing summary SHALL NOT prevent project history from loading
