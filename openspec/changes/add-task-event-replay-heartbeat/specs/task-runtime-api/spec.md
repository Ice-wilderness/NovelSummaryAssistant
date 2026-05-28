## ADDED Requirements

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

## MODIFIED Requirements

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
