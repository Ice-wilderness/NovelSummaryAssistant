## MODIFIED Requirements

### Requirement: Small-Summary-Only Execution
The system SHALL support generating only small summaries without advancing to later summary stages.

#### Scenario: Stop after small summary
- **WHEN** a task starts with the small-summary-only option
- **THEN** the backend SHALL execute pending small-summary work
- **AND** the backend SHALL stop before big summary, super summary, and ultimate summary stages

#### Scenario: Use independently of trigger scan
- **WHEN** the user starts a small-summary-only task
- **THEN** the backend SHALL treat it as a novel summary preparation task rather than a trigger scan prerequisite
- **AND** trigger scanning SHALL NOT require the generated small summaries before scanning original chapter text
