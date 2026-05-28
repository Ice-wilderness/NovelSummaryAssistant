## ADDED Requirements

### Requirement: Replayable Task Event Subscription
The WebUI workbench SHALL track task event IDs and use replay cursors when reconnecting to task event streams so retained events are not silently missed.

#### Scenario: Track latest task event ID
- **WHEN** the WebUI receives a task event with an `event_id`
- **THEN** it SHALL remember the latest processed event ID for that task
- **AND** it SHALL keep existing task status and log behavior unchanged for event payloads that do not include an event ID

#### Scenario: Reconnect with replay cursor
- **WHEN** a task event stream reconnects after the WebUI has processed an event ID for that task
- **THEN** the WebUI SHALL request the stream with the latest processed event ID as the replay cursor
- **AND** replayed retained events SHALL update the visible logs, progress, warnings, and task state before live events continue

#### Scenario: Ignore duplicate replayed event
- **WHEN** the WebUI receives an event whose task ID and event ID were already processed
- **THEN** it SHALL ignore that duplicate event
- **AND** it SHALL NOT append duplicate log lines or regress visible task state

#### Scenario: Preserve status fallback after stream error
- **WHEN** the task event stream errors, disconnects, or reports a replay gap
- **THEN** the WebUI SHALL request the latest task status from the backend
- **AND** visible task controls and project status SHALL update from that task status response

### Requirement: Task Event Heartbeat Handling
The WebUI workbench SHALL handle backend heartbeat frames as connection-liveness signals without showing them as user-visible task events.

#### Scenario: Receive heartbeat
- **WHEN** the WebUI receives a heartbeat frame for an active task stream
- **THEN** it SHALL treat the stream as connected
- **AND** it SHALL NOT append the heartbeat to user-visible logs or task history

#### Scenario: Continue existing terminal behavior
- **WHEN** a replayed or live task event reports `success`, `failed`, `cancelled`, `partial_failed`, or `interrupted`
- **THEN** the WebUI SHALL refresh the latest task status from the backend
- **AND** it SHALL close the active subscription for that task after the terminal state is visible
