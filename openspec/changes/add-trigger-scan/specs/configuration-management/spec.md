## ADDED Requirements

### Requirement: Trigger Profile Configuration Store
The system SHALL manage trigger profile files as local configuration data.

#### Scenario: Load trigger profiles
- **WHEN** the WebUI loads trigger profile configuration
- **THEN** the backend SHALL read profiles from `workspace/trigger_profiles/` and return public profile data without exposing unrelated configuration secrets

#### Scenario: Save trigger profile configuration
- **WHEN** the user saves trigger profile changes
- **THEN** the backend SHALL validate and persist those changes atomically enough to avoid corrupting existing profiles on write failure

### Requirement: Novel Summary Defaults
The system SHALL persist user defaults for novel summary workflow settings.

#### Scenario: Load novel summary defaults
- **WHEN** the WebUI opens novel summary configuration
- **THEN** the backend SHALL return saved novel summary defaults when available
- **AND** the backend SHALL default `summary_batch_size` to 10 and `summary_output_format` to `md` when no saved value exists

#### Scenario: Save novel summary output format default
- **WHEN** the user saves novel summary defaults
- **THEN** the backend SHALL persist `summary_output_format` as either `md` or `txt`

#### Scenario: Validate novel summary defaults
- **WHEN** the user saves novel summary defaults
- **THEN** the backend SHALL reject non-positive `summary_batch_size` values and any `summary_output_format` outside `md` or `txt`

### Requirement: Trigger Scan Defaults
The system SHALL persist user defaults for trigger scan configuration.

#### Scenario: Save scan defaults
- **WHEN** the user saves default trigger scan settings
- **THEN** the backend SHALL persist scan mode, minimum confidence, low-confidence retention, verification preference, `coarse_summary_batch_size`, `precise_chapter_batch_size`, `verification_chapter_batch_size`, maximum evidence quote length, and skip-advice preference

#### Scenario: Load scan defaults
- **WHEN** the WebUI opens trigger scan configuration
- **THEN** the backend SHALL return saved defaults or safe documented defaults
- **AND** the safe documented defaults SHALL include `coarse_summary_batch_size` 3, `precise_chapter_batch_size` 5, and `verification_chapter_batch_size` 5

#### Scenario: Validate scan defaults
- **WHEN** the user saves trigger scan defaults
- **THEN** the backend SHALL reject invalid confidence, non-positive batch size, quote length, or mode values with actionable errors

### Requirement: Trigger Scan API Selection
The system SHALL allow trigger scan configuration to reference existing enabled API configurations.

#### Scenario: Select scan APIs
- **WHEN** the user starts a trigger scan
- **THEN** the backend SHALL resolve selected scan API identifiers using the existing API configuration store

#### Scenario: Select verification API
- **WHEN** the user enables verification and selects a verification API
- **THEN** the backend SHALL resolve that API identifier using the existing API configuration store

#### Scenario: Reject missing API
- **WHEN** a trigger scan request references an unknown or disabled API configuration
- **THEN** the backend SHALL reject the request before creating a task
