## MODIFIED Requirements

### Requirement: Trigger Scan Defaults
The system SHALL persist user defaults for trigger scan configuration.

#### Scenario: Save scan defaults
- **WHEN** the user saves default trigger scan settings
- **THEN** the backend SHALL persist minimum confidence, low-confidence retention, verification preference, `precise_chapter_batch_size`, `verification_chapter_batch_size`, maximum evidence quote length, and skip-advice preference
- **AND** the backend SHALL NOT persist `coarse_summary_batch_size` as an active trigger scan setting

#### Scenario: Load scan defaults
- **WHEN** the WebUI opens trigger scan configuration
- **THEN** the backend SHALL return saved defaults or safe documented defaults
- **AND** the safe documented defaults SHALL include `precise_chapter_batch_size` 5 and `verification_chapter_batch_size` 5
- **AND** legacy saved defaults with `scan_mode` set to `hybrid` SHALL be returned as precise-scan defaults

#### Scenario: Validate scan defaults
- **WHEN** the user saves trigger scan defaults
- **THEN** the backend SHALL reject invalid confidence, non-positive batch size, quote length, or any mode value other than `precise` with actionable errors
