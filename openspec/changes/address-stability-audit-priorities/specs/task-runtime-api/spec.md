## MODIFIED Requirements

### Requirement: Task Control Operations
The backend SHALL support pause, resume, and cancel operations for running tasks where the underlying workflow supports them. User-initiated cancellation accepted before another terminal state SHALL converge to a `cancelled` terminal state rather than being reported as `failed` or successful completion.

#### Scenario: Cancel running task
- **WHEN** the WebUI requests cancellation for a running task and the task accepts cancellation before reaching another terminal state
- **THEN** the backend SHALL signal cancellation and eventually move the task to a `cancelled` terminal state
- **AND** business workflow runners SHALL NOT convert the cancellation into a normal result or failed result

#### Scenario: Cancel already terminal task
- **WHEN** the WebUI requests cancellation for a task that has already reached a terminal state
- **THEN** the backend SHALL preserve the existing terminal state and return an actionable response

### Requirement: API Failure Diagnostics
The backend task runtime SHALL write one readable diagnostic file for each failed API attempt. Diagnostic files SHALL preserve complete non-secret input and output content by default for troubleshooting, while still redacting API keys, authorization headers, and other secret credentials.

#### Scenario: Log failed API attempt
- **WHEN** an API attempt fails due to request error, HTTP error, response parsing error, invalid response shape, or minimum output length validation
- **THEN** the backend SHALL write a single formatted JSON diagnostic file for that failed attempt in a dedicated API failure-log directory

#### Scenario: Avoid combined failure log
- **WHEN** multiple API attempts fail during a task
- **THEN** the backend SHALL create separate formatted JSON files for each failure instead of appending all failures into one JSONL-style file

#### Scenario: Redact sensitive diagnostic fields
- **WHEN** the backend writes an API failure diagnostic file
- **THEN** the file SHALL omit or redact API keys, authorization headers, and other secret credentials

#### Scenario: Include complete troubleshooting context
- **WHEN** the backend writes an API failure diagnostic file
- **THEN** the file SHALL include task stage, project or chapter context when available, API display name, attempt number, error type, status code when available, traceback or error summary, complete non-secret request input, and complete response content when available

#### Scenario: Clean diagnostic logs without truncating new failures
- **WHEN** the user or maintainer invokes an API failure-log cleanup path
- **THEN** the backend SHALL remove matching old diagnostic files according to the configured cleanup policy
- **AND** newly written failure diagnostics SHALL continue preserving complete non-secret input and output content by default

## ADDED Requirements

### Requirement: Terminal Event Stream Completion
The backend SHALL make terminal task state observable through the realtime event stream and SHALL avoid leaving clients waiting indefinitely after the terminal state is emitted.

#### Scenario: End stream after terminal event
- **WHEN** a task event stream emits a terminal state event for `completed`, `failed`, `cancelled`, or `partial_failed`
- **THEN** the server-side stream SHALL end or otherwise signal completion in a way that lets the WebUI stop waiting for more task events

#### Scenario: Query terminal status after stream interruption
- **WHEN** a task event stream is interrupted before the WebUI receives a terminal event
- **THEN** the WebUI SHALL be able to query the task status endpoint to recover the latest known task state
