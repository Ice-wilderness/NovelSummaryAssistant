## MODIFIED Requirements

### Requirement: Trigger Scan Output Directory
The system SHALL store trigger scan artifacts under the managed project's output directory.

#### Scenario: Resolve trigger scan output directory
- **WHEN** a trigger scan task starts for a managed project
- **THEN** the backend SHALL resolve the scan output directory as `<effective_project_output>/trigger_scan/`

#### Scenario: Create trigger scan output directory
- **WHEN** the scan output directory does not exist
- **THEN** the backend SHALL create it before writing reports, history, or exports
