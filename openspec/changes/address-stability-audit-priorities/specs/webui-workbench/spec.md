## ADDED Requirements

### Requirement: Task Status Recovery And Terminal Display
The WebUI workbench SHALL recover task status after event stream interruptions and display the backend terminal state without remapping cancellation or partial failure to generic failure.

#### Scenario: Refresh task after event stream error
- **WHEN** a task event stream reports an error or disconnects before a terminal event
- **THEN** the WebUI SHALL request the latest task status from the backend
- **AND** the page SHALL update visible task controls and project status from that response

#### Scenario: Display cancelled task
- **WHEN** the backend reports a task state of `cancelled`
- **THEN** the WebUI SHALL display the task as cancelled rather than failed or completed

#### Scenario: Display partial failed scan
- **WHEN** a trigger scan report or task summary reports `partial_failed`
- **THEN** the WebUI SHALL display the partial failure state and preserve access to available findings, events, and warnings

### Requirement: Trigger Scan Warning Display
The WebUI workbench SHALL display trigger scan warnings that affect report trustworthiness.

#### Scenario: Show unverified finding warning
- **WHEN** a trigger scan report contains an `unverified` warning
- **THEN** the WebUI SHALL show that warning near the report summary or affected result area

#### Scenario: Show deterministic aggregation status
- **WHEN** the user views trigger scan prompt settings or scan result metadata
- **THEN** the WebUI SHALL make clear that current event aggregation is deterministic and not controlled by an LLM aggregation prompt
