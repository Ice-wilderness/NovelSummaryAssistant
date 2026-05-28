## ADDED Requirements

### Requirement: Corrupt Configuration Recovery
The system SHALL preserve corrupted local configuration files before falling back to defaults and SHALL expose recoveries as configuration-domain warnings.

#### Scenario: Recover corrupted API configuration
- **WHEN** the backend loads the local API configuration file and cannot parse it as valid configuration data
- **THEN** the backend SHALL copy the corrupted file to a sibling `.bak` file before using default API configuration values
- **AND** the configuration response SHALL include a warning associated with API configuration recovery

#### Scenario: Recover corrupted user settings
- **WHEN** the backend loads local user settings and cannot parse them as valid settings data
- **THEN** the backend SHALL copy the corrupted file to a sibling `.bak` file before using default user setting values
- **AND** the settings response SHALL include a warning associated with user settings recovery

#### Scenario: Recover corrupted chapter pattern configuration
- **WHEN** the backend loads local chapter pattern configuration and cannot parse it as valid pattern data
- **THEN** the backend SHALL copy the corrupted file to a sibling `.bak` file before using default chapter pattern values
- **AND** the pattern response SHALL include a warning associated with chapter pattern recovery

#### Scenario: Backup cannot be written
- **WHEN** the backend detects corrupted configuration data but cannot write the `.bak` copy
- **THEN** the backend SHALL still use safe default values
- **AND** the response warning SHALL state that the corrupted file could not be backed up
