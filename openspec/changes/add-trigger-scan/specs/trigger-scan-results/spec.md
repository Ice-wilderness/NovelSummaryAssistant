## ADDED Requirements

### Requirement: Scan Report Persistence
The system SHALL persist each trigger scan as an independent report under the project's trigger scan output directory.

#### Scenario: Save completed report
- **WHEN** a trigger scan completes
- **THEN** the backend SHALL save the ScanReport under `exports/{project_slug}/trigger_scan/`
- **AND** the report SHALL include report id, project slug, profile snapshot, scan mode, scan range, scan config, status, summary, events, and findings

#### Scenario: Preserve failed partial report
- **WHEN** a trigger scan fails after producing partial results
- **THEN** the backend SHALL preserve a partial report or recovery state with status `failed`

#### Scenario: List report history
- **WHEN** the WebUI opens scan results for a project
- **THEN** the backend SHALL return that project's scan report history with date, profile name, scan mode, scan range, and status

### Requirement: Spoiler Level Display
The system SHALL store and display three spoiler levels for findings and events.

#### Scenario: Store spoiler levels
- **WHEN** a finding or event is saved
- **THEN** it SHALL include low, standard, and detailed spoiler descriptions where available

#### Scenario: Global spoiler slider
- **WHEN** the user changes the global spoiler slider
- **THEN** the WebUI SHALL update all visible findings and events to the selected spoiler level without new API calls

#### Scenario: Per-item spoiler override
- **WHEN** the user changes a single result's spoiler level
- **THEN** that result SHALL display the selected level while other results continue using the global level

#### Scenario: Detailed evidence quote
- **WHEN** the spoiler level is low or standard
- **THEN** the WebUI SHALL NOT show `evidence_quote`
- **AND** when the spoiler level is detailed the WebUI MAY show `evidence_quote` limited by scan configuration

### Requirement: Result Views And Filtering
The system SHALL provide event and finding views with filters.

#### Scenario: Show event view
- **WHEN** a report contains ScanEvents
- **THEN** the WebUI SHALL show an event view by default with each event's rule, related chapters, max severity, confidence, main-plot flag, and selected spoiler summary

#### Scenario: Expand event findings
- **WHEN** the user expands an event
- **THEN** the WebUI SHALL show the findings linked to that event with chapter and paragraph locations

#### Scenario: Show finding table
- **WHEN** the user switches to the finding view
- **THEN** the WebUI SHALL show findings in a filterable table including rule, chapter, paragraph ids, severity, confidence, description, main-plot flag, review status, and actions

#### Scenario: Apply filters
- **WHEN** the user filters by trigger type, severity, confidence, chapter range, review status, main plot, or high risk
- **THEN** the WebUI SHALL update the visible results without modifying saved report data

### Requirement: Context Review
The system SHALL allow users to inspect original context around a finding.

#### Scenario: Open context modal
- **WHEN** the user selects view context for a finding
- **THEN** the WebUI SHALL display the matched chapter with the matched paragraph ids highlighted
- **AND** the modal SHALL include nearby paragraphs before and after the hit when available

#### Scenario: Missing context
- **WHEN** the original chapter file or paragraph index is unavailable
- **THEN** the WebUI SHALL show an actionable warning instead of fabricating context

### Requirement: Finding Review Actions
The system SHALL persist user review actions on scan findings.

#### Scenario: Mark false positive
- **WHEN** the user marks a finding as a false positive
- **THEN** the backend SHALL update that finding's `review_status` to `false_positive`

#### Scenario: Mark confirmed
- **WHEN** the user marks a finding as confirmed
- **THEN** the backend SHALL update that finding's `review_status` to `confirmed`

#### Scenario: Add user note
- **WHEN** the user saves a note on a finding
- **THEN** the backend SHALL persist the note with the finding

### Requirement: Skip List
The system SHALL maintain a user-controlled skip list independent from scan reports.

#### Scenario: Add finding to skip list
- **WHEN** the user adds a finding to the skip list
- **THEN** the backend SHALL save chapter file, chapter title, paragraph range, rule name, severity, user note, and source finding id

#### Scenario: View skip list by chapter
- **WHEN** the user opens the skip list
- **THEN** the WebUI SHALL group skip items by chapter

#### Scenario: Export skip list
- **WHEN** the user exports the skip list
- **THEN** the backend SHALL generate a Markdown file containing chapter headings, paragraph ranges, trigger names, severity, and notes

### Requirement: Report Export
The system SHALL export trigger scan reports as Markdown and JSON.

#### Scenario: Export JSON report
- **WHEN** the user exports a scan report as JSON
- **THEN** the backend SHALL write a structured JSON report preserving all report fields

#### Scenario: Export Markdown report
- **WHEN** the user exports a scan report as Markdown
- **THEN** the backend SHALL write a readable report containing scan configuration, overview, trigger events, pending review findings, and the AI auxiliary warning

#### Scenario: Limit quoted evidence
- **WHEN** a Markdown report includes evidence quotes
- **THEN** each quote SHALL respect the configured maximum evidence quote length

### Requirement: AI Auxiliary Warning
The system SHALL clearly warn that trigger scan results are advisory.

#### Scenario: Show warning in results page
- **WHEN** the user views scan results
- **THEN** the WebUI SHALL show that AI scan results are for auxiliary reference and cannot guarantee all triggers are found

#### Scenario: Include warning in exported Markdown
- **WHEN** the backend exports a Markdown report
- **THEN** the report SHALL include the same advisory warning
