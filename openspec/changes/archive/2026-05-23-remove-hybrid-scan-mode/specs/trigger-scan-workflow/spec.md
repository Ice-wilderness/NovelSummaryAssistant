## MODIFIED Requirements

### Requirement: Scan Mode Preconditions
The system SHALL validate trigger scan prerequisites before spending API calls.

#### Scenario: Precise scan requires chapter files
- **WHEN** the user starts a trigger scan
- **THEN** the backend SHALL require readable single-chapter files for the selected scan range

#### Scenario: Reject hybrid mode
- **WHEN** the WebUI or an API client submits a trigger scan request with `scan_mode` set to `hybrid`
- **THEN** the backend SHALL reject the request with an actionable validation error explaining that trigger scanning now uses original-text precise scan only

#### Scenario: Do not require small summaries
- **WHEN** the user starts a trigger scan for a project whose selected chapters have no small-summary coverage
- **THEN** the backend SHALL allow the scan to start when the selected chapter files and scan configuration are otherwise valid

### Requirement: Precise Chapter Scan
The system SHALL scan original chapter text for every selected chapter and require evidence-backed JSON findings.

#### Scenario: Precise scan full range
- **WHEN** a trigger scan starts
- **THEN** the backend SHALL run precise scanning against every chapter in the selected scan range

#### Scenario: Precise scan batches chapters
- **WHEN** precise scanning runs against original chapter text
- **THEN** the backend SHALL read chapters in batches controlled by `precise_chapter_batch_size`
- **AND** the default `precise_chapter_batch_size` SHALL be 5
- **AND** the backend SHALL preserve per-chapter paragraph ids in each batched request

#### Scenario: Enforce finding evidence
- **WHEN** the model returns a finding
- **THEN** the backend SHALL require rule id, severity, confidence, paragraph ids, main-plot flag, three spoiler levels, and detailed evidence quote
- **AND** findings without valid paragraph ids or acceptable evidence SHALL NOT be marked as confirmed scan output

#### Scenario: Apply rule thresholds
- **WHEN** a model finding has severity below the rule's severity threshold
- **THEN** the backend SHALL exclude it from formal findings unless low-confidence or review settings explicitly retain it for review

### Requirement: Realtime Scan Progress
The system SHALL stream scan progress, logs, and intermediate findings.

#### Scenario: Emit stage progress
- **WHEN** a trigger scan task runs
- **THEN** the backend SHALL emit structured events for precise scan, verification, aggregation, and report writing stages

#### Scenario: Emit chapter progress
- **WHEN** a chapter completes
- **THEN** the backend SHALL emit scanned chapter count, total chapter count, and current stage progress text

#### Scenario: Append intermediate finding
- **WHEN** a chapter produces findings before the full report is complete
- **THEN** the WebUI SHALL be able to append those findings to the results view without waiting for task completion

## REMOVED Requirements

### Requirement: Hybrid Coarse Scan
**Reason**: Hybrid coarse scan depends on small summaries that do not reliably map back to single chapter files, creating an unrecoverable missed-chapter failure mode before precise scanning.
**Migration**: Use original-text precise scanning for every selected chapter, with `precise_chapter_batch_size` controlling request batch size.

#### Scenario: Coarse scan batches summaries
- **WHEN** hybrid scanning starts
- **THEN** the backend SHALL send small summaries in batches controlled by `coarse_summary_batch_size`
- **AND** the default `coarse_summary_batch_size` SHALL be 3

#### Scenario: Coarse scan with verification enabled
- **WHEN** verification is enabled for hybrid mode
- **THEN** the coarse scan SHALL return suspected chapters and suspected rule ids without treating coarse output as final findings

#### Scenario: Coarse scan with verification disabled
- **WHEN** verification is disabled and coarse output includes complete findings
- **THEN** the backend SHALL still run precise scanning for chapters that require original-text evidence before finalizing paragraph-level findings
