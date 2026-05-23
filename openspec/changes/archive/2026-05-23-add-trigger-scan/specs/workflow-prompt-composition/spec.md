## MODIFIED Requirements

### Requirement: Workflow Prompt Pages
The system SHALL present prompt configuration grouped by actual application workflow.

#### Scenario: View workflow prompt tabs
- **WHEN** the user opens the prompt editor page
- **THEN** the system SHALL show separate workflow pages or tabs for workflows that use LLM prompts, including novel summarization, article summarization, and trigger scanning

#### Scenario: View workflow without prompt nodes
- **WHEN** a workflow does not use persistent LLM prompt nodes
- **THEN** the system SHALL clearly indicate that the workflow has no editable persistent prompt nodes instead of showing unrelated templates

## ADDED Requirements

### Requirement: Trigger Scan Prompt Nodes
The system SHALL provide editable workflow prompt nodes for every AI-assisted trigger scan stage.

#### Scenario: View trigger scan prompt nodes
- **WHEN** the user opens the trigger scanning prompt workflow
- **THEN** the prompt editor SHALL show nodes for coarse scan, precise scan, verification, and aggregation

#### Scenario: Save trigger scan prompt node
- **WHEN** the user edits and saves a trigger scan prompt node
- **THEN** subsequent trigger scan tasks SHALL use the saved messages for that stage

#### Scenario: Reset trigger scan prompt node
- **WHEN** the user resets one trigger scan prompt node
- **THEN** the backend SHALL restore only that node to its default messages

### Requirement: Trigger Scan Prompt Variables
The system SHALL validate variables used by trigger scan prompt nodes.

#### Scenario: Render precise scan prompt
- **WHEN** the backend renders the precise scan prompt
- **THEN** it SHALL provide trigger rules JSON, scan settings, chapter text with paragraph ids, maximum quote length, skip-advice setting, and output JSON schema variables

#### Scenario: Render verification prompt
- **WHEN** the backend renders the verification prompt
- **THEN** it SHALL provide trigger rules, referenced paragraph context, first-pass findings, and verification output schema variables

#### Scenario: Reject missing trigger prompt variable
- **WHEN** a trigger scan prompt references a variable not supplied by the scan workflow
- **THEN** the backend SHALL reject prompt rendering with a clear error identifying the missing variable and prompt node
