## MODIFIED Requirements

### Requirement: Realtime Scan Progress
The system SHALL stream scan progress, logs, and intermediate findings.

#### Scenario: Emit stage progress
- **WHEN** a trigger scan task runs
- **THEN** the backend SHALL emit structured events for precise scan, verification, aggregation, and report writing stages
- **AND** each stage progress event SHALL include a `data.stages` array containing all scan stages with their `id`, `label`, `completed`, `total`, and `status` fields
- **AND** the event SHALL include `data.current_stage` to identify the active stage

#### Scenario: Emit chapter progress
- **WHEN** a chapter completes
- **THEN** the backend SHALL emit scanned chapter count, total chapter count, and current stage progress text
- **AND** the `data.stages` array in the event SHALL reflect the updated completed count for the current stage

#### Scenario: Append intermediate finding
- **WHEN** a chapter produces findings before the full report is complete
- **THEN** the WebUI SHALL be able to append those findings to the results view without waiting for task completion
