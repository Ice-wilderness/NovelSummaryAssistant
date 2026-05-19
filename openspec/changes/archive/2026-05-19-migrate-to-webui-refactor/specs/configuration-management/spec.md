## ADDED Requirements

### Requirement: API Configuration Management
The system SHALL allow the user to create, edit, enable, disable, delete, save, and load API configurations through the WebUI.

#### Scenario: Save API configuration
- **WHEN** the user saves valid API configuration entries
- **THEN** the backend SHALL persist the entries in the local configuration store and SHALL preserve stable API identifiers

### Requirement: API Secret Protection
The system SHALL protect API keys from accidental exposure in the WebUI, logs, and backend responses.

#### Scenario: Load saved API configuration
- **WHEN** the WebUI loads saved API configuration entries
- **THEN** the backend SHALL NOT return full API key values unless an explicit edit flow requires them

### Requirement: API Key Environment Override
The system SHALL support API keys stored in local configuration files and SHALL allow environment variables to override configured key values at runtime.

#### Scenario: Environment key is available
- **WHEN** an API configuration references an environment variable that exists
- **THEN** the backend SHALL use the environment variable value as the effective API key

#### Scenario: Environment key is missing
- **WHEN** an API configuration references an environment variable that does not exist
- **THEN** the backend SHALL fall back to the locally configured API key if one is available

### Requirement: Prompt Management
The system SHALL allow the user to view, edit, save, reset, and use prompt templates through the WebUI.

#### Scenario: Save prompt template
- **WHEN** the user saves a prompt template
- **THEN** the backend SHALL persist it in the prompt cache and subsequent tasks SHALL use the saved template

### Requirement: Word Count And Task Settings
The system SHALL expose word count settings and task parameters as structured configuration rather than UI widget state.

#### Scenario: Validate numeric task setting
- **WHEN** the user submits a task setting that must be a positive integer
- **THEN** the backend SHALL validate the value before starting the task and SHALL return a clear error if validation fails

### Requirement: Existing Data Compatibility
The system SHALL preserve compatibility with existing local API config files, prompt cache files, and `.summarizer_cache` task state where practical.

#### Scenario: Load existing project data
- **WHEN** the WebUI starts in a project with existing configuration and cache files
- **THEN** the backend SHALL load compatible data without requiring the user to recreate settings manually

### Requirement: Configuration Defaults
The system SHALL provide safe defaults for missing optional configuration fields.

#### Scenario: Missing optional field
- **WHEN** a saved configuration lacks an optional field introduced by the WebUI migration
- **THEN** the backend SHALL supply a documented default and SHALL keep the configuration usable
