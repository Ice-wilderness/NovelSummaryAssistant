## MODIFIED Requirements

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

### Requirement: Structured Trigger Scan Events
The backend task runtime SHALL stream structured events for trigger scan progress and intermediate results.

#### Scenario: Stream scan progress event
- **WHEN** a scan stage or chapter progresses
- **THEN** the backend SHALL emit an event containing stage name, completed count, total count, stages array, current stage, and progress text

#### Scenario: Stream intermediate result event
- **WHEN** a chapter produces findings before the scan completes
- **THEN** the backend SHALL emit an event containing enough finding summary data for the WebUI to append it to the current result list
