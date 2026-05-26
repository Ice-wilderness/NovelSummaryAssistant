## ADDED Requirements

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
