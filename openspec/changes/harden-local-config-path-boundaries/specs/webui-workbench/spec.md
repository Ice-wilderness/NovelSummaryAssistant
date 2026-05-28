## ADDED Requirements

### Requirement: Local Configuration Warning Display
The WebUI workbench SHALL display local configuration recovery warnings in the page or control surface where the user can act on the affected configuration.

#### Scenario: Display API configuration recovery warning
- **WHEN** the API configuration response includes a recovery warning for corrupted API configuration data
- **THEN** the WebUI SHALL display that warning in the API configuration page or API configuration section

#### Scenario: Display user settings recovery warning
- **WHEN** the user settings response includes a recovery warning for corrupted user settings data
- **THEN** the WebUI SHALL display that warning in the user settings page or settings section

#### Scenario: Display chapter pattern recovery warning
- **WHEN** the chapter pattern response includes a recovery warning for corrupted chapter pattern data
- **THEN** the WebUI SHALL display that warning in the chapter pattern or chapter splitting surface that loads those patterns

### Requirement: Output Directory Validation Recovery
The WebUI workbench SHALL make invalid output directory failures recoverable through an explicit user action rather than silently changing the output target.

#### Scenario: Show default fallback action
- **WHEN** saving a project or starting a task fails because the project-level custom output directory is invalid
- **THEN** the WebUI SHALL show the validation error near the output directory control
- **AND** the WebUI SHALL show an action that lets the user switch to the effective default output directory

#### Scenario: Use default output directory after confirmation
- **WHEN** the user chooses the default output directory fallback action after a custom output directory validation failure
- **THEN** the WebUI SHALL clear the project-level custom output directory from the next save or task-start request
- **AND** the WebUI SHALL display the effective default output directory as the output target

#### Scenario: Preserve invalid path for correction
- **WHEN** the backend rejects an invalid project-level custom output directory
- **THEN** the WebUI SHALL keep the invalid path visible for editing until the user changes it or chooses the default fallback action

### Requirement: Local Path Capability Error Display
The WebUI workbench SHALL display local path capability failures at the control that initiated the action.

#### Scenario: Display local picker unavailable error
- **WHEN** a file or directory picker request fails because the local GUI picker is unavailable
- **THEN** the WebUI SHALL display the actionable error near the picker control that initiated the request

#### Scenario: Display open output directory error
- **WHEN** opening the project output directory fails
- **THEN** the WebUI SHALL display the actionable error near the open-directory control
