# trigger-scan-workflow Specification

## Purpose
TBD - created by archiving change add-trigger-scan. Update Purpose after archive.
## Requirements
### Requirement: Trigger Scan Task
The system SHALL run trigger scans as managed long-running tasks attached to existing novel projects.

#### Scenario: Start trigger scan task
- **WHEN** the WebUI submits a valid trigger scan request for a managed novel project
- **THEN** the backend SHALL create a managed trigger scan task and return a task identifier

#### Scenario: Reject non-novel project
- **WHEN** the WebUI submits a trigger scan request for a project that is not a novel summary or chapter-split project with chapter files
- **THEN** the backend SHALL reject the request with an actionable validation error

#### Scenario: Enforce single running task
- **WHEN** another long-running task is already running
- **THEN** the WebUI SHALL prevent starting a trigger scan task until the running task reaches a terminal state

### Requirement: Scan Mode Preconditions
The system SHALL validate scan mode prerequisites before spending API calls.

#### Scenario: Precise mode requires chapter files
- **WHEN** the user selects precise mode
- **THEN** the backend SHALL require readable single-chapter files for the selected scan range

#### Scenario: Hybrid mode requires small summary coverage
- **WHEN** the user selects hybrid mode
- **THEN** the backend SHALL verify small-summary coverage for the selected scan range before starting the scan

#### Scenario: Partial summary coverage
- **WHEN** hybrid mode summary coverage does not include the full selected scan range
- **THEN** the WebUI SHALL offer to scan only covered chapters, use precise mode for uncovered chapters, generate missing small summaries, or cancel

### Requirement: Paragraph Preprocessing
The system SHALL preprocess chapters into stable paragraph-indexed text before precise scanning.

#### Scenario: Assign paragraph ids
- **WHEN** a chapter is prepared for scanning
- **THEN** the backend SHALL assign stable paragraph ids such as `P001`, `P002`, and `P003`
- **AND** the model input SHALL include chapter file, chapter title, and paragraph ids

#### Scenario: Cache paragraph index
- **WHEN** a chapter is preprocessed
- **THEN** the backend SHALL cache the paragraph index under `.summarizer_cache/paragraph_index/`

#### Scenario: Reuse unchanged paragraph index
- **WHEN** a previously indexed chapter has not changed
- **THEN** the backend SHALL reuse the cached paragraph ids for subsequent scans

### Requirement: Hybrid Coarse Scan
The system SHALL use small summaries to identify suspected chapters in hybrid mode.

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

### Requirement: Precise Chapter Scan
The system SHALL scan original chapter text and require evidence-backed JSON findings.

#### Scenario: Precise scan suspected chapters
- **WHEN** hybrid mode has identified suspected chapters
- **THEN** the backend SHALL run precise scanning against the original text for those chapters

#### Scenario: Precise scan full range
- **WHEN** precise mode starts
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

### Requirement: Optional Verification
The system SHALL optionally verify findings using the same or different API configuration.

#### Scenario: Verify chapter findings
- **WHEN** verification is enabled
- **THEN** the backend SHALL submit findings from each chapter together with the referenced paragraph context for verification

#### Scenario: Verification batches chapters
- **WHEN** verification processes findings from multiple chapters
- **THEN** the backend SHALL batch chapter finding groups according to `verification_chapter_batch_size`
- **AND** the default `verification_chapter_batch_size` SHALL be 5
- **AND** findings from the same chapter SHALL remain in the same verification group

#### Scenario: Apply verification result
- **WHEN** verification marks a finding false positive
- **THEN** the backend SHALL either remove it from verified findings or retain it only in the pending review area according to scan configuration

#### Scenario: Select independent verification API
- **WHEN** the user chooses a verification API
- **THEN** the backend SHALL use that API for verification calls instead of the scan API when available

### Requirement: Finding Aggregation
The system SHALL aggregate related findings into events while preserving original findings.

#### Scenario: Merge adjacent findings
- **WHEN** findings share chapter, rule, and adjacent paragraph ids
- **THEN** the backend SHALL merge them into a single finding before event aggregation

#### Scenario: Aggregate cross-chapter event
- **WHEN** findings appear to describe the same trigger event across chapters
- **THEN** the backend SHALL use the aggregation prompt to propose a ScanEvent with related finding ids and three spoiler-level summaries

#### Scenario: Preserve standalone findings
- **WHEN** a finding is not assigned to an event
- **THEN** the report SHALL keep it as a standalone finding

### Requirement: Chapter-Level Resume
The system SHALL support chapter-level checkpointing for trigger scans.

#### Scenario: Save chapter completion
- **WHEN** a chapter completes scan processing
- **THEN** the backend SHALL save scan state to `.summarizer_cache/scan_state_{task_id}.json`

#### Scenario: Resume interrupted scan
- **WHEN** the user resumes an interrupted scan with compatible configuration
- **THEN** the backend SHALL continue from the first incomplete chapter
- **AND** the backend SHALL NOT repeat completed chapter API calls

#### Scenario: Reject incompatible batch configuration on resume
- **WHEN** the user resumes an interrupted scan after changing scan batch configuration
- **THEN** the backend SHALL treat the saved scan state as configuration-incompatible or require the user to confirm a full rescan

#### Scenario: Cancel scan
- **WHEN** the user cancels a running trigger scan task
- **THEN** the backend SHALL preserve completed chapter results and mark the task cancelled

### Requirement: Realtime Scan Progress
The system SHALL stream scan progress, logs, and intermediate findings.

#### Scenario: Emit stage progress
- **WHEN** a trigger scan task runs
- **THEN** the backend SHALL emit structured events for coarse scan, precise scan, verification, aggregation, and report writing stages

#### Scenario: Emit chapter progress
- **WHEN** a chapter completes
- **THEN** the backend SHALL emit scanned chapter count, total chapter count, and current stage progress text

#### Scenario: Append intermediate finding
- **WHEN** a chapter produces findings before the full report is complete
- **THEN** the WebUI SHALL be able to append those findings to the results view without waiting for task completion

