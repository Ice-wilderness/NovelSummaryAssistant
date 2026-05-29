## ADDED Requirements

### Requirement: API Attempt Count Configuration
The system SHALL present API retry configuration using wording that matches its stored total-attempt semantics.

#### Scenario: Display API attempt count field
- **WHEN** the WebUI displays the API configuration field backed by `max_retries`
- **THEN** the field label, hint, or tooltip SHALL describe the value as API total attempts including the initial request
- **AND** the WebUI SHALL NOT describe the field only as additional retry count

#### Scenario: Save API attempt count
- **WHEN** the user saves API configuration with a valid `max_retries` value
- **THEN** the backend SHALL persist the value using the existing total-attempt semantics
- **AND** the save operation SHALL NOT reinterpret the value as additional retries

#### Scenario: Load existing API retry configuration
- **WHEN** the backend loads an existing API configuration containing `max_retries`
- **THEN** the system SHALL treat the saved value as the maximum total attempts for each API request
- **AND** the system SHALL NOT silently migrate or increment the value to compensate for old UI wording
