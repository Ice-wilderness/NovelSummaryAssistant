## MODIFIED Requirements

### Requirement: Optional Verification
The system SHALL optionally verify findings using the same or different API configuration. Verification SHALL include new findings from the current run and historical findings whose verification state is missing or unknown when their paragraph context can be reconstructed.

#### Scenario: Verify chapter findings
- **WHEN** verification is enabled
- **THEN** the backend SHALL submit new findings from each chapter together with the referenced paragraph context for verification

#### Scenario: Verify unresolved historical findings on resume
- **WHEN** a resumed scan includes historical findings whose verification state is missing or unknown
- **THEN** the backend SHALL rebuild paragraph context for those findings when possible and submit them for verification

#### Scenario: Preserve historical findings without context
- **WHEN** a resumed scan includes a historical finding that cannot be matched to readable chapter context
- **THEN** the backend SHALL preserve the finding without fabricating context
- **AND** the report SHALL include an `unverified` warning for that finding or chapter

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
The system SHALL aggregate related findings into events while preserving original findings. During this change, event aggregation SHALL use deterministic local logic and SHALL NOT call an LLM aggregation prompt.

#### Scenario: Merge adjacent findings
- **WHEN** findings share chapter, rule, and adjacent paragraph ids
- **THEN** the backend SHALL merge them into a single finding before event aggregation

#### Scenario: Aggregate cross-chapter event
- **WHEN** findings appear to describe the same trigger event across chapters
- **THEN** the backend SHALL use deterministic local aggregation logic to produce ScanEvent records with related finding ids and spoiler-level summaries
- **AND** the backend SHALL NOT require or call the aggregation prompt for this stage

#### Scenario: Preserve standalone findings
- **WHEN** a finding is not assigned to an event
- **THEN** the report SHALL keep it as a standalone finding

### Requirement: Chapter-Level Resume
The system SHALL support chapter-level checkpointing for trigger scans and SHALL preserve a stable progress denominator based on the user's selected scan range.

#### Scenario: Save chapter completion
- **WHEN** a chapter completes scan processing
- **THEN** the backend SHALL save scan state to `.summarizer_cache/scan_state_{task_id}.json`

#### Scenario: Resume interrupted scan
- **WHEN** the user resumes an interrupted scan with compatible configuration
- **THEN** the backend SHALL continue from the first incomplete chapter
- **AND** the backend SHALL NOT repeat completed chapter API calls
- **AND** progress events SHALL report completed count as resumed completed chapters plus chapters processed in the current run over the full selected chapter count

#### Scenario: Reject incompatible batch configuration on resume
- **WHEN** the user resumes an interrupted scan after changing scan batch configuration
- **THEN** the backend SHALL treat the saved scan state as configuration-incompatible or require the user to confirm a full rescan

#### Scenario: Cancel scan
- **WHEN** the user cancels a running trigger scan task
- **THEN** the backend SHALL preserve completed chapter results and mark the task cancelled

### Requirement: Realtime Scan Progress
The system SHALL stream scan progress, logs, and intermediate findings using progress totals that remain stable across fresh scans and resumed scans.

#### Scenario: Emit stage progress
- **WHEN** a trigger scan task runs
- **THEN** the backend SHALL emit structured events for precise scan, verification, aggregation, and report writing stages
- **AND** each stage progress event SHALL include a `data.stages` array containing all scan stages with their `id`, `label`, `completed`, `total`, and `status` fields
- **AND** the event SHALL include `data.current_stage` to identify the active stage

#### Scenario: Emit chapter progress
- **WHEN** a chapter completes
- **THEN** the backend SHALL emit scanned chapter count, total selected chapter count, and current stage progress text
- **AND** the `data.stages` array in the event SHALL reflect the cumulative completed count for the current stage

#### Scenario: Append intermediate finding
- **WHEN** a chapter produces findings before the full report is complete
- **THEN** the WebUI SHALL be able to append those findings to the results view without waiting for task completion

## ADDED Requirements

### Requirement: Pausable Trigger Scan Execution
The trigger scan workflow SHALL honor pause requests before starting additional scan or verification API calls.

#### Scenario: Pause before next API call
- **WHEN** the user pauses a running trigger scan before the next precise scan or verification request starts
- **THEN** the backend SHALL wait for resume before starting that API request

#### Scenario: Resume paused scan
- **WHEN** the user resumes a paused trigger scan
- **THEN** the backend SHALL continue scanning from the next pending unit without resetting completed progress
