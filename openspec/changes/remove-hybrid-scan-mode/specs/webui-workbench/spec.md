## MODIFIED Requirements

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
- **THEN** the page SHALL show scan range, scan API selection, minimum confidence, low-confidence retention, skip-advice generation, `precise_chapter_batch_size`, `verification_chapter_batch_size`, verification toggle, verification API, and maximum evidence quote length
- **AND** the page SHALL NOT show a scan mode selector or `coarse_summary_batch_size` control

#### Scenario: Run startup checks before scan
- **WHEN** the user clicks start scan
- **THEN** the page SHALL run backend startup checks and present required user decisions before starting the long-running task
- **AND** those decisions SHALL NOT include generating missing small summaries, scanning only summary-covered chapters, or switching from hybrid to precise mode
