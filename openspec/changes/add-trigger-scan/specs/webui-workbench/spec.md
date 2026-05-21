## MODIFIED Requirements

### Requirement: Core Workflow Navigation
The WebUI workbench SHALL provide navigable views for novel summarization, article summarization, custom summarization, chapter splitting, trigger scanning, prompt editing, API configuration, and logs.

#### Scenario: Switch workflow
- **WHEN** the user selects a workflow view
- **THEN** the workbench SHALL display the controls and status relevant to that workflow without losing unsaved form state in other views

#### Scenario: Open trigger scanning view
- **WHEN** the user selects the trigger scanning navigation item
- **THEN** the workbench SHALL display trigger profile management, scan configuration, and scan results tabs

## ADDED Requirements

### Requirement: Trigger Scan Workbench
The WebUI workbench SHALL provide a dedicated trigger scan page for managed novel projects.

#### Scenario: Show trigger scan tabs
- **WHEN** the user opens the trigger scan page
- **THEN** the page SHALL provide tabs for profile management, scan configuration, and scan results

#### Scenario: Select project for trigger scan
- **WHEN** the user configures a trigger scan
- **THEN** the page SHALL let the user select an existing managed novel or chapter-split project with readable chapter files

#### Scenario: Show scan configuration controls
- **WHEN** the user configures a scan
- **THEN** the page SHALL show scan range, scan mode, scan API selection, minimum confidence, low-confidence retention, skip-advice generation, coarse batch size, verification toggle, verification API, and maximum evidence quote length

#### Scenario: Run startup checks before scan
- **WHEN** the user clicks start scan
- **THEN** the page SHALL run backend startup checks and present required user decisions before starting the long-running task
