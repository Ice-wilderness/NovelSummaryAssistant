## ADDED Requirements

### Requirement: Local WebUI Entry
The system SHALL provide a local browser-based workbench as the primary user interface for the application.

#### Scenario: Open workbench
- **WHEN** the user starts the WebUI entry command
- **THEN** the system SHALL start a local server and expose a browser-accessible workbench URL

#### Scenario: Existing desktop entry is not primary
- **WHEN** the user uses the legacy desktop entry after migration
- **THEN** the system SHALL either launch the WebUI workflow or clearly indicate how to open the WebUI

### Requirement: Core Workflow Navigation
The WebUI workbench SHALL provide navigable views for novel summarization, article summarization, custom summarization, chapter splitting, prompt editing, API configuration, and logs.

#### Scenario: Switch workflow
- **WHEN** the user selects a workflow view
- **THEN** the workbench SHALL display the controls and status relevant to that workflow without losing unsaved form state in other views

### Requirement: Task Control Surface
The WebUI workbench SHALL allow the user to start, pause, resume, and cancel supported long-running tasks from the browser.

#### Scenario: Control running task
- **WHEN** a supported task is running
- **THEN** the workbench SHALL show available task controls and SHALL disable actions that are invalid for the current task state

### Requirement: Live Logs And Progress
The WebUI workbench SHALL show live global logs, task progress, and API-specific logs while a task is running.

#### Scenario: Receive task log
- **WHEN** the backend emits a task log event
- **THEN** the workbench SHALL append it to the global log view and SHALL route API-specific events to the corresponding API log view

### Requirement: Modern Responsive Layout
The WebUI workbench SHALL use a modern responsive layout that remains usable on common desktop and tablet browser widths.

#### Scenario: Resize browser
- **WHEN** the browser viewport changes between desktop and tablet widths
- **THEN** the workbench SHALL keep primary navigation, forms, task controls, and logs visible or reachable without overlapping content

### Requirement: Project Attribution
The WebUI workbench SHALL display project attribution for the original author and current author.

#### Scenario: View attribution
- **WHEN** the user opens the workbench attribution area or project information view
- **THEN** the workbench SHALL show original author `zhoufei_1314` and current author `Ice_wilderness`
