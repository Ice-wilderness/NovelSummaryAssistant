## ADDED Requirements

### Requirement: Interrupted Task Recovery Display

The WebUI workbench SHALL display backend-reported `interrupted` task status as a restart interruption that requires user action, not as normal failure, success, cancellation, or partial failure.

#### Scenario: Display interrupted task in shared status surface
- **WHEN** the backend reports a task status of `interrupted`
- **THEN** the shared task status surface SHALL label the task as interrupted
- **AND** it SHALL show an actionable message explaining that the backend restarted before the task finished and the user may need to restart or continue from project progress

#### Scenario: Disable controls for interrupted task
- **WHEN** the current task has status `interrupted`
- **THEN** the WebUI SHALL NOT show pause, resume, or cancel as valid actions for that task
- **AND** starting a new supported task SHALL remain available when other validation requirements are met

#### Scenario: Display interrupted status in project history
- **WHEN** a historical project reports `latest_task_status` as `interrupted`
- **THEN** the project history control SHALL show a distinct interrupted status label
- **AND** the project name SHALL remain readable without appending ambiguous failure text

### Requirement: Persisted Terminal Task Display

The WebUI workbench SHALL preserve backend terminal task states loaded from persisted summaries.

#### Scenario: Display persisted cancelled task
- **WHEN** a task status query after backend restart returns `cancelled`
- **THEN** the WebUI SHALL display the task as cancelled rather than failed or completed

#### Scenario: Display persisted partial failed task
- **WHEN** a task status query after backend restart returns `partial_failed`
- **THEN** the WebUI SHALL display the task as a partial result
- **AND** it SHALL preserve available warnings and result details returned by the backend

#### Scenario: Display persisted failed task
- **WHEN** a task status query after backend restart returns `failed`
- **THEN** the WebUI SHALL display the task as failed with the backend-provided error or result summary

#### Scenario: Display persisted successful task
- **WHEN** a task status query after backend restart returns `success`
- **THEN** the WebUI SHALL display the task as completed with the backend-provided result summary when available
