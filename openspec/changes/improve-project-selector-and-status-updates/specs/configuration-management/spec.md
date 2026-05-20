## ADDED Requirements

### Requirement: User Default Export Directory
The system SHALL allow the user to configure one user-level default export directory for managed workflow outputs.

#### Scenario: Save user default export directory
- **WHEN** the user saves a valid user-level default export directory
- **THEN** the backend SHALL persist the directory and subsequent managed workflows SHALL use it before the current fallback default export directory

#### Scenario: Load user default export directory
- **WHEN** the WebUI loads configuration
- **THEN** the backend SHALL return the saved user-level default export directory so the WebUI can display and edit it

#### Scenario: Clear user default export directory
- **WHEN** the user clears the user-level default export directory
- **THEN** subsequent managed workflows SHALL use the current fallback default export directory unless a project-level custom output directory is provided

#### Scenario: Reject invalid user default export directory
- **WHEN** the user saves a path that cannot be used as a directory
- **THEN** the backend SHALL reject the value with a clear validation error and SHALL keep the previous valid configuration
