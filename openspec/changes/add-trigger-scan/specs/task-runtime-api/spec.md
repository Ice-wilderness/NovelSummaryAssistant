## MODIFIED Requirements

### Requirement: Unified Task Model
The backend SHALL represent novel summarization, article summarization, custom summarization, chapter splitting, trigger scanning, small-summary-only preparation, and model fetching as managed tasks with a consistent task model.

#### Scenario: Start managed task
- **WHEN** the WebUI requests a supported task with valid parameters
- **THEN** the backend SHALL create a task identifier and return its initial status

## ADDED Requirements

### Requirement: Trigger Scan Task API
The backend task API SHALL expose operations needed to validate, start, observe, cancel, and resume trigger scan tasks.

#### Scenario: Validate trigger scan request
- **WHEN** the WebUI submits trigger scan configuration for startup checks
- **THEN** the backend SHALL return whether the request is ready to start or which user decisions are required

#### Scenario: Start trigger scan
- **WHEN** startup checks pass and the WebUI starts a trigger scan
- **THEN** the backend SHALL create a `trigger_scan` task using the unified task runtime

#### Scenario: Query trigger scan task
- **WHEN** the WebUI queries a running trigger scan task
- **THEN** the backend SHALL return task status, lifecycle state, progress text, timestamps, latest result summary, and scan-specific progress metadata when available

### Requirement: Structured Trigger Scan Events
The backend task runtime SHALL stream structured events for trigger scan progress and intermediate results.

#### Scenario: Stream scan progress event
- **WHEN** a scan stage or chapter progresses
- **THEN** the backend SHALL emit an event containing stage name, completed count, total count, and progress text

#### Scenario: Stream intermediate result event
- **WHEN** a chapter produces findings before the scan completes
- **THEN** the backend SHALL emit an event containing enough finding summary data for the WebUI to append it to the current result list

### Requirement: Small Summary Only Task Mode
The backend task API SHALL support running only the small-summary stage for a novel project.

#### Scenario: Start small-summary-only task
- **WHEN** the WebUI requests small-summary-only preparation for a valid novel project
- **THEN** the backend SHALL start a managed task that stops after small summaries are complete

#### Scenario: Reject unsupported small-summary-only request
- **WHEN** the request does not identify a valid novel project with chapter files
- **THEN** the backend SHALL return a validation error and SHALL NOT start a task
