## ADDED Requirements

### Requirement: Reconciled Project Status Display

The WebUI workbench SHALL display project reconciliation status distinctly from task lifecycle status when historical or imported project outputs are missing or inconsistent.

#### Scenario: Display abnormal completed project in history
- **WHEN** a historical project summary reports reconciliation status `abnormal_completed`
- **THEN** the history control SHALL show a distinct abnormal-completed label or warning indicator
- **AND** the project name SHALL remain readable without appending ambiguous failure text

#### Scenario: Display abnormal completed project details
- **WHEN** the user selects a project with reconciliation status `abnormal_completed`
- **THEN** the page SHALL show that the project previously completed or partially completed but current outputs are missing or inconsistent
- **AND** the page SHALL show the backend-provided reconciliation warnings near the affected project status or output area

#### Scenario: Do not treat abnormal completed as normal completion
- **WHEN** a selected project has reconciliation status `abnormal_completed`
- **THEN** the WebUI SHALL NOT present missing outputs as available
- **AND** the WebUI SHALL NOT hide the warning merely because the latest task status is `success` or `partial_failed`

#### Scenario: Do not treat abnormal completed as ordinary incomplete
- **WHEN** a selected project has reconciliation status `abnormal_completed`
- **THEN** the WebUI SHALL preserve the historical terminal task status in the task or history surface
- **AND** the page SHALL explain that the current issue is output inconsistency rather than a task that never completed

#### Scenario: Display incomplete state separately
- **WHEN** a selected project has no reliable completed state and no generated output
- **THEN** the WebUI SHALL display the project as incomplete without using the abnormal-completed warning

#### Scenario: Display incomplete metadata warning
- **WHEN** generated output exists but state metadata is incomplete
- **THEN** the WebUI SHALL show a warning that the project state is incomplete and may need review
- **AND** the WebUI SHALL keep available output links or status details visible when they are safe to use

### Requirement: Project Repair Controls

The WebUI workbench SHALL provide repair controls for projects with repairable reconciliation warnings and SHALL require user confirmation before starting repairs that may call an LLM API or overwrite existing outputs.

#### Scenario: Show repair plan
- **WHEN** a selected project response includes a repair plan
- **THEN** the page SHALL show available repair actions, blocked actions, required inputs, and expected output effects using backend-provided descriptions

#### Scenario: Start non-LLM repair
- **WHEN** the user starts a repair action that does not require an LLM API call and does not overwrite existing output
- **THEN** the WebUI SHALL call the repair task API with the selected action identifier
- **AND** the page SHALL subscribe to and display the repair task's progress like other managed tasks

#### Scenario: Confirm LLM repair
- **WHEN** the user starts a repair action that may call an LLM API or produce text that differs from the original result
- **THEN** the WebUI SHALL show a confirmation that names the possible cost and output-variance implications before calling the repair task API

#### Scenario: Confirm overwrite repair
- **WHEN** the user starts a repair action that may overwrite an existing generated output
- **THEN** the WebUI SHALL require explicit overwrite confirmation before calling the repair task API

#### Scenario: Show blocked repair
- **WHEN** a repair plan marks an action as blocked
- **THEN** the WebUI SHALL show the blocked reason and SHALL NOT present that blocked action as a runnable primary action

#### Scenario: Refresh project after repair terminal state
- **WHEN** a repair task reaches `success`, `partial_failed`, `failed`, or `cancelled`
- **THEN** the WebUI SHALL refresh the project details and history summary so the latest reconciliation status and warnings are visible

#### Scenario: Repair API validation failure
- **WHEN** the backend rejects a repair start request because the plan is stale, blocked, or missing required confirmation
- **THEN** the WebUI SHALL show the validation message and refresh the repair plan before allowing another repair attempt
