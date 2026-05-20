## Purpose
Define how the WebUI manages local API configuration, prompt templates, task settings, secrets, defaults, and compatibility with existing project data.

## Requirements

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
The system SHALL allow the user to view, edit, save, reset, and use prompt templates through the WebUI, including structured workflow prompt nodes with ordered role-based messages and reusable modules.

#### Scenario: Save prompt template
- **WHEN** the user saves a prompt template or workflow prompt node
- **THEN** the backend SHALL persist it in the prompt cache and subsequent tasks SHALL use the saved template or node configuration

#### Scenario: Save role-based messages
- **WHEN** the user saves a prompt node containing multiple messages
- **THEN** the backend SHALL persist each message's role, order, and content without flattening the node into a single text field

#### Scenario: Reset prompt template
- **WHEN** the user resets a prompt template or prompt node
- **THEN** the backend SHALL restore only the selected template or node to its default content and SHALL leave other prompt nodes and modules unchanged

### Requirement: Structured Prompt Persistence
The system SHALL persist workflow prompt configuration as structured data that preserves workflows, nodes, messages, roles, ordering, and module references.

#### Scenario: Save structured prompt configuration
- **WHEN** the user saves a workflow prompt configuration
- **THEN** the backend SHALL store the full structured configuration and SHALL preserve message order, role, content, and module references

#### Scenario: Load structured prompt configuration
- **WHEN** the WebUI loads prompt configuration after a previous structured save
- **THEN** the backend SHALL return the saved workflows, nodes, messages, roles, ordering, modules, and dirty/reset metadata needed by the WebUI

### Requirement: Prompt Module Persistence
The system SHALL persist reusable prompt modules independently from individual prompt nodes.

#### Scenario: Save prompt module
- **WHEN** the user saves a prompt module
- **THEN** the backend SHALL persist the module with a stable identifier, display name, optional description, and content

#### Scenario: Delete prompt module
- **WHEN** the user deletes a prompt module that is still referenced by prompt nodes
- **THEN** the backend SHALL reject the deletion or require the references to be removed first with a clear error

### Requirement: Word Count And Task Settings
The system SHALL expose word count settings and task parameters as structured configuration rather than UI widget state.

#### Scenario: Validate numeric task setting
- **WHEN** the user submits a task setting that must be a positive integer
- **THEN** the backend SHALL validate the value before starting the task and SHALL return a clear error if validation fails

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

### Requirement: Minimum Output Character Count
The system SHALL allow the user to configure a minimum output character count for validating API-generated summary content.

#### Scenario: Save minimum output character count
- **WHEN** the user saves a non-negative minimum output character count
- **THEN** the backend SHALL persist the value and subsequent API output validation SHALL use it

#### Scenario: Load minimum output character count
- **WHEN** the WebUI loads configuration
- **THEN** the backend SHALL return the saved minimum output character count so the WebUI can display and edit it

#### Scenario: Disable minimum output character count
- **WHEN** the saved minimum output character count is zero
- **THEN** the backend SHALL treat minimum output length validation as disabled

#### Scenario: Reject invalid minimum output character count
- **WHEN** the user saves a negative or non-integer minimum output character count
- **THEN** the backend SHALL reject the value with a clear validation error and SHALL keep the previous valid configuration

### Requirement: Existing Data Compatibility
The system SHALL preserve compatibility with existing local API config files, prompt cache files, structured prompt configuration files, and `.summarizer_cache` task state where practical.

#### Scenario: Load existing project data
- **WHEN** the WebUI starts in a project with existing configuration and cache files
- **THEN** the backend SHALL load compatible data without requiring the user to recreate settings manually

#### Scenario: Load legacy prompt cache
- **WHEN** structured prompt configuration does not exist but legacy `prompt_cache/*.txt` files exist
- **THEN** the backend SHALL initialize workflow prompt nodes from the legacy files and SHALL preserve existing edited prompt text

#### Scenario: Prefer structured prompt configuration
- **WHEN** both structured prompt configuration and legacy prompt text files exist
- **THEN** the backend SHALL treat the structured configuration as the source of truth and SHALL NOT silently overwrite it with legacy text files

### Requirement: Configuration Defaults
The system SHALL provide safe defaults for missing optional configuration fields.

#### Scenario: Missing optional field
- **WHEN** a saved configuration lacks an optional field introduced by the WebUI migration
- **THEN** the backend SHALL supply a documented default and SHALL keep the configuration usable
