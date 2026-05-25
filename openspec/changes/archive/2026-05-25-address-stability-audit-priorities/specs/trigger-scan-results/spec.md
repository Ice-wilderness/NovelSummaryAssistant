## MODIFIED Requirements

### Requirement: Scan Report Persistence
The system SHALL persist each trigger scan as an independent report under the project's trigger scan output directory. A report status of `completed` SHALL mean every selected chapter was scanned and all required post-scan stages completed without blocking errors.

#### Scenario: Save completed report
- **WHEN** a trigger scan completes every selected chapter and finishes verification, aggregation, and report writing without blocking errors
- **THEN** the backend SHALL save the ScanReport under `exports/{project_slug}/trigger_scan/`
- **AND** the report SHALL include report id, project slug, profile snapshot, scan mode, scan range, scan config, status `completed`, summary, events, and findings

#### Scenario: Preserve failed partial report
- **WHEN** a trigger scan fails after producing partial results and at least one selected chapter was not scanned
- **THEN** the backend SHALL preserve a partial report or recovery state with status `partial_failed`
- **AND** the report SHALL identify unscanned chapters, failed stage, warnings, and available findings or events

#### Scenario: Preserve failed complete-range report
- **WHEN** every selected chapter was scanned but a later stage fails before a complete report can be produced
- **THEN** the backend SHALL preserve available scan data with status `partial_failed`
- **AND** the report SHALL identify the failed post-scan stage and any missing derived outputs

#### Scenario: List report history
- **WHEN** the WebUI opens scan results for a project
- **THEN** the backend SHALL return that project's scan report history with date, profile name, scan mode, scan range, and status

## ADDED Requirements

### Requirement: Report Verification Warnings
The system SHALL preserve and display warnings when scan results contain findings that could not be verified with reconstructed paragraph context.

#### Scenario: Save unverified warning
- **WHEN** a finding is preserved without verification because its paragraph context is unavailable
- **THEN** the report SHALL include a warning identifying the affected finding or chapter

#### Scenario: Display unverified warning
- **WHEN** the WebUI displays a report containing unverified findings
- **THEN** the WebUI SHALL show an actionable warning instead of presenting those findings as fully verified

### Requirement: Report Status Meaning
The system SHALL distinguish complete success, partial failure, cancellation, and ordinary failure in trigger scan report and task surfaces.

#### Scenario: Completed requires full selected range
- **WHEN** any selected chapter remains unscanned due to a non-cancel failure
- **THEN** the report status SHALL NOT be `completed`

#### Scenario: Cancelled task preserves partial artifacts
- **WHEN** the user cancels a trigger scan after partial results exist
- **THEN** the task SHALL be `cancelled`
- **AND** any preserved report artifacts SHALL NOT be marked `completed`
