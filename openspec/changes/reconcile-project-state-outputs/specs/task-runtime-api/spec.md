## ADDED Requirements

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
