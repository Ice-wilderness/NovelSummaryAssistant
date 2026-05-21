## ADDED Requirements

### Requirement: Trigger Scan Output Directory
The system SHALL store trigger scan artifacts under the managed project's output directory.

#### Scenario: Resolve trigger scan output directory
- **WHEN** a trigger scan task starts for a managed project
- **THEN** the backend SHALL resolve the scan output directory as `<effective_project_output>/trigger_scan/`

#### Scenario: Create trigger scan output directory
- **WHEN** the scan output directory does not exist
- **THEN** the backend SHALL create it before writing reports, history, exports, or skip lists

### Requirement: Trigger Scan History Files
The system SHALL keep trigger scan history scoped to the project that produced it.

#### Scenario: Save report history index
- **WHEN** a trigger scan report is saved
- **THEN** the backend SHALL update that project's trigger scan history index

#### Scenario: Load report history from imported project
- **WHEN** the user imports an existing project directory containing trigger scan reports
- **THEN** the backend SHALL detect those reports and expose them in the project's recognized status

### Requirement: Trigger Scan Artifacts On Project Deletion
The system SHALL handle trigger scan artifacts consistently with other managed outputs when a project is deleted.

#### Scenario: Delete managed trigger scan output
- **WHEN** the user deletes a managed project whose trigger scan output is under the managed export directory
- **THEN** the backend SHALL remove the trigger scan artifacts with the rest of that managed output directory

#### Scenario: Preserve unmanaged trigger scan output
- **WHEN** the user deletes a project whose custom output directory is outside the managed default export directory
- **THEN** the backend SHALL NOT delete that custom output directory or its trigger scan artifacts

### Requirement: Migration Status Recognition
The system SHALL include chapter granularity and trigger scan artifacts in project status recognition.

#### Scenario: Recognize single-chapter project
- **WHEN** an imported or historical project contains single-chapter files
- **THEN** the backend SHALL report that trigger scanning can use precise mode if other required scan configuration is supplied

#### Scenario: Recognize legacy grouped project
- **WHEN** an imported or historical project contains grouped chapter files
- **THEN** the backend SHALL report that migration is required before trigger scanning
