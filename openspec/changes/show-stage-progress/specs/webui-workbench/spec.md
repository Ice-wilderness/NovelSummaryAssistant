## MODIFIED Requirements

### Requirement: Live Logs And Progress
The WebUI workbench SHALL show live global logs, task progress, and API-specific logs while a task is running.

#### Scenario: Receive task log
- **WHEN** the backend emits a task log event
- **THEN** the workbench SHALL append it to the global log view and SHALL route API-specific events to the corresponding API log view

#### Scenario: Display stage progress bar
- **WHEN** the user is on a novel summary or trigger scan page with a project loaded
- **THEN** the workbench SHALL display a stage progress bar that covers all workflow stages
- **AND** the progress bar SHALL show the current stage, completed stages, and pending stages with distinct visual treatment
- **AND** the progress bar SHALL update in real time when a task is running

#### Scenario: Show current stage remaining
- **WHEN** a task is running
- **THEN** the progress bar SHALL display how many items remain in the current stage as a completed/total count

#### Scenario: Show overall workflow progress
- **WHEN** the user views the progress bar
- **THEN** the workbench SHALL enable the user to understand at a glance which stage is executing and how many stages have been completed and how many remain

## ADDED Requirements

### Requirement: Stage Progress On Project Entry
The WebUI workbench SHALL display stage progress immediately when entering a project, based on available file-system and cache state.

#### Scenario: Enter project with completed stages
- **WHEN** the user selects a historical project that has completed summary stages
- **THEN** the workbench SHALL immediately show which stages are completed, which stage was in progress, and which stages are pending

#### Scenario: Enter project with trigger scan results
- **WHEN** the user selects a historical project that has trigger scan results
- **THEN** the workbench SHALL show trigger scan stage progress alongside summary stage progress when relevant
