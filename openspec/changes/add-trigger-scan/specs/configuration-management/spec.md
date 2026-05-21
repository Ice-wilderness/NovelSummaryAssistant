## ADDED Requirements

### Requirement: Trigger Profile Configuration Store
The system SHALL manage trigger profile files as local configuration data.

#### Scenario: Load trigger profiles
- **WHEN** the WebUI loads trigger profile configuration
- **THEN** the backend SHALL read profiles from `workspace/trigger_profiles/` and return public profile data without exposing unrelated configuration secrets

#### Scenario: Save trigger profile configuration
- **WHEN** the user saves trigger profile changes
- **THEN** the backend SHALL validate and persist those changes atomically enough to avoid corrupting existing profiles on write failure

### Requirement: Trigger Scan Defaults
The system SHALL persist user defaults for trigger scan configuration.

#### Scenario: Save scan defaults
- **WHEN** the user saves default trigger scan settings
- **THEN** the backend SHALL persist scan mode, minimum confidence, low-confidence retention, verification preference, coarse batch size, maximum evidence quote length, and skip-advice preference

#### Scenario: Load scan defaults
- **WHEN** the WebUI opens trigger scan configuration
- **THEN** the backend SHALL return saved defaults or safe documented defaults

#### Scenario: Validate scan defaults
- **WHEN** the user saves trigger scan defaults
- **THEN** the backend SHALL reject invalid confidence, batch size, quote length, or mode values with actionable errors

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
