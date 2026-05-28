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
The backend SHALL support pause, resume, and cancel operations for running tasks where the underlying workflow supports them. User-initiated cancellation accepted before another terminal state SHALL converge to a `cancelled` terminal state rather than being reported as `failed` or successful completion.

#### Scenario: Cancel running task
- **WHEN** the WebUI requests cancellation for a running task
- **THEN** the backend SHALL signal cancellation and eventually move the task to a `cancelled` terminal state
- **AND** business workflow runners SHALL NOT convert the cancellation into a normal result or failed result

#### Scenario: Cancel already terminal task
- **WHEN** the WebUI requests cancellation for a task that has already reached a terminal state
- **THEN** the backend SHALL preserve the existing terminal state and return an actionable response

### Requirement: Realtime Event Stream
The backend SHALL provide a realtime event stream for task logs and progress updates.

#### Scenario: Subscribe to events
- **WHEN** the WebUI subscribes to a task event stream
- **THEN** the backend SHALL emit structured events for logs, progress updates, state changes, warnings, and failures

#### Scenario: Emit stage progress for novel summary
- **WHEN** a novel summary task runs and transitions to a new stage or completes a unit within a stage
- **THEN** the backend SHALL emit a structured progress event containing a `data.stages` array with all workflow stages, each including `id`, `label`, `completed`, `total`, and `status`
- **AND** the event SHALL include `data.current_stage` identifying the active stage

#### Scenario: Emit stage progress for trigger scan
- **WHEN** a trigger scan task runs and transitions to a new stage or completes a chapter batch
- **THEN** the backend SHALL emit a structured progress event containing a `data.stages` array with all scan stages, each including `id`, `label`, `completed`, `total`, and `status`
- **AND** the event SHALL include `data.current_stage` identifying the active stage

### Requirement: Terminal Event Stream Completion
The backend SHALL make terminal task state observable through the realtime event stream and SHALL avoid leaving clients waiting indefinitely after the terminal state is emitted.

#### Scenario: End stream after terminal event
- **WHEN** a task event stream emits a terminal state event for `completed`, `failed`, `cancelled`, or `partial_failed`
- **THEN** the server-side stream SHALL end or otherwise signal completion in a way that lets the WebUI stop waiting for more task events

#### Scenario: Query terminal status after stream interruption
- **WHEN** a task event stream is interrupted before the WebUI receives a terminal event
- **THEN** the WebUI SHALL be able to query the task status endpoint to recover the latest known task state

### Requirement: Summary Partial Failure Task State
The backend task runtime SHALL support `partial_failed` as a terminal task state for article summary and custom summary tasks that preserve usable output while reporting incomplete input coverage.

#### Scenario: Article summary returns partial outcome
- **WHEN** an article summary runner reports a partial outcome with generated final output and failed section details
- **THEN** the backend task runtime SHALL mark the task status as `partial_failed`
- **AND** the task status endpoint SHALL return the generated result summary, warnings, and failed section details
- **AND** the realtime event stream SHALL emit a terminal event with status `partial_failed`

#### Scenario: Custom summary returns partial outcome
- **WHEN** a custom summary runner reports a partial outcome with generated output and failed material details
- **THEN** the backend task runtime SHALL mark the task status as `partial_failed`
- **AND** the task status endpoint SHALL return the generated result summary, warnings, and failed material details
- **AND** the realtime event stream SHALL emit a terminal event with status `partial_failed`

#### Scenario: Existing string runner behavior is preserved
- **WHEN** an existing task runner returns a plain string result instead of a structured outcome
- **THEN** the backend task runtime SHALL preserve the existing success and failure mapping for that runner

#### Scenario: Partial failure is terminal
- **WHEN** a task reaches status `partial_failed`
- **THEN** the task runtime SHALL set a finished timestamp
- **AND** task control operations SHALL treat the task as terminal

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
- **THEN** the backend SHALL emit an event containing stage name, completed count, total count, stages array, current stage, and progress text

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

### Requirement: Replayable Task Event Log
The backend task runtime SHALL assign durable, monotonically increasing event IDs to task events and SHALL persist retained task events in a bounded per-task event log for replay through the task event stream.

#### Scenario: Assign durable event IDs
- **WHEN** the task runtime emits a task event
- **THEN** the event SHALL include an `event_id`
- **AND** event IDs for the same task SHALL increase in emission order
- **AND** the event ID SHALL be included in task status API event payloads and SSE event frames

#### Scenario: Replay retained events after cursor
- **WHEN** the WebUI subscribes to `/api/tasks/{task_id}/events` with a valid `Last-Event-ID` header or equivalent replay cursor
- **THEN** the backend SHALL emit retained events for that task whose event IDs are greater than the cursor
- **AND** replayed events SHALL be emitted in original event ID order before newer live events

#### Scenario: Subscribe without replay cursor
- **WHEN** the WebUI subscribes to a running task event stream without a replay cursor
- **THEN** the backend SHALL stream new live events for that task
- **AND** the backend MAY emit a current state event before live events so the client can initialize visible task status

#### Scenario: Recover from unavailable replay range
- **WHEN** the WebUI requests replay from a cursor that is invalid or older than retained task events
- **THEN** the backend SHALL NOT fail the stream solely because the full replay range is unavailable
- **AND** the backend SHALL emit a current task state event or replay-gap event that lets the WebUI refresh task status
- **AND** the stream SHALL continue with live events for active tasks or close after making inactive task state observable

### Requirement: Task Event Stream Heartbeat
The backend task event stream SHALL emit heartbeat frames while an active task stream is idle so clients can distinguish an idle task from a broken connection.

#### Scenario: Emit heartbeat while active stream is idle
- **WHEN** a task event stream is open for an active task and no task event is emitted within the heartbeat interval
- **THEN** the backend SHALL emit a heartbeat frame on the SSE connection
- **AND** the heartbeat SHALL NOT change task lifecycle state

#### Scenario: Heartbeat does not advance replay cursor
- **WHEN** the backend emits a heartbeat frame
- **THEN** the heartbeat SHALL NOT be persisted as a task event
- **AND** the heartbeat SHALL NOT advance the durable task event cursor used for `Last-Event-ID` replay

### Requirement: Task Event Retention And Cleanup
The backend task runtime SHALL keep persisted task event logs bounded by local retention rules so event replay does not grow disk usage without limit.

#### Scenario: Prune task event log beyond retention
- **WHEN** a task event log exceeds the configured retention limit
- **THEN** the backend SHALL remove older replayable events while preserving enough current state or terminal state information for task observation

#### Scenario: Cleanup old task event logs
- **WHEN** the task runtime starts or writes task events
- **THEN** the backend SHALL apply event-log cleanup rules to remove stale task event data according to configured defaults
- **AND** cleanup failures SHALL NOT prevent the backend from starting or tasks from running

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
The backend task event stream SHALL make persisted terminal and interrupted task states observable and SHALL replay retained task events when a bounded event log is available, without promising recovery of events outside retention.

#### Scenario: Subscribe to persisted terminal task
- **WHEN** the WebUI subscribes to events for a task that was loaded from a persisted terminal summary
- **THEN** the backend SHALL replay retained events after the supplied replay cursor when retained events are available
- **AND** the backend SHALL emit or expose the terminal state and close the stream after making the terminal state observable
- **AND** the backend SHALL NOT be required to replay historical log or progress events that were pruned by retention or were never persisted in the event log

#### Scenario: Subscribe to interrupted task
- **WHEN** the WebUI subscribes to events for an interrupted task
- **THEN** the backend SHALL replay retained events after the supplied replay cursor when retained events are available
- **AND** the backend SHALL emit or expose the interrupted state and close the stream
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

### Requirement: Project Output Repair Task API
The backend task API SHALL expose user-triggered repair operations for managed projects whose reconciliation status indicates missing or inconsistent outputs.

#### Scenario: Request repair plan
- **WHEN** the WebUI requests repair information for a managed project
- **THEN** the backend SHALL return the latest reconciliation status and repair plan before any repair task is started

#### Scenario: Start repair action
- **WHEN** the user starts a repair action from a repair plan and the request includes the selected action identifier
- **THEN** the backend SHALL create a managed repair task and return its task identifier and initial status
- **AND** the repair task SHALL use the same task status query and realtime event stream surfaces as other managed tasks

#### Scenario: Require confirmation for LLM repair
- **WHEN** a selected repair action may call an LLM API or produce newly generated text that can differ from the original output
- **THEN** the backend SHALL reject the repair start request unless the request includes explicit confirmation for that cost and output-variance disclosure

#### Scenario: Summary content repair requires LLM confirmation
- **WHEN** a selected repair action would create or replace small-summary, big-summary, super-summary, ultimate-summary, article-summary, or custom-summary text
- **THEN** the backend SHALL treat the action as an LLM repair
- **AND** the backend SHALL reject the repair start request unless the request includes explicit confirmation for LLM usage and possible content differences

#### Scenario: Require confirmation for overwrite repair
- **WHEN** a selected repair action may overwrite an existing generated output file
- **THEN** the backend SHALL reject the repair start request unless the request includes explicit overwrite confirmation

#### Scenario: Reject stale repair action
- **WHEN** the requested repair action no longer matches the latest reconciliation result for the project
- **THEN** the backend SHALL reject the repair start request with a validation error requiring the client to refresh the repair plan

#### Scenario: Reject blocked repair action
- **WHEN** the requested repair action is blocked because required inputs, settings, or API configuration are missing
- **THEN** the backend SHALL return a clear validation error and SHALL NOT start a repair task

#### Scenario: Repair task emits progress
- **WHEN** a repair task rebuilds final outputs or reruns missing workflow stages
- **THEN** the task runtime SHALL emit progress, warning, failure, and terminal state events that describe the current repair phase

#### Scenario: Repair task completes
- **WHEN** a repair task successfully restores all outputs required by the selected repair action
- **THEN** the task SHALL finish with status `success`
- **AND** the backend SHALL refresh and persist the project's reconciliation result

#### Scenario: Repair task partially restores outputs
- **WHEN** a repair task restores some requested outputs but one or more repair units fail while usable repaired output remains
- **THEN** the task SHALL finish with status `partial_failed`
- **AND** the task status SHALL include warnings and failed repair-unit details
- **AND** the backend SHALL refresh the project's reconciliation result

#### Scenario: Repair task fails without usable output
- **WHEN** a repair task cannot restore any requested output
- **THEN** the task SHALL finish with status `failed`
- **AND** the project SHALL retain its previous reconciliation warnings unless the latest reconcile detects a more specific failure

### Requirement: Repair Task Boundary
The backend task runtime SHALL keep project repair separate from normal task resume semantics so abnormal completed projects are not silently treated as unfinished tasks.

#### Scenario: Abnormal completed project does not auto resume
- **WHEN** a project is classified as `abnormal_completed`
- **THEN** the task runtime SHALL NOT automatically resume a summary or trigger scan workflow when the project is loaded
- **AND** repair SHALL require a selected repair action

#### Scenario: Repair task does not rewrite original task history
- **WHEN** a repair task starts or finishes for a project with an earlier completed task record
- **THEN** the backend SHALL preserve the original task record
- **AND** the repair task SHALL be recorded as a separate task associated with the same managed project

#### Scenario: Repair unavailable for unsupported workflow
- **WHEN** a project workflow type has no repair implementation
- **THEN** the repair plan SHALL report that repair is unsupported for that workflow
- **AND** the task API SHALL reject repair start requests for that unsupported workflow
