## ADDED Requirements

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

## MODIFIED Requirements

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
