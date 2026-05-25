## Purpose
Define workflow-level prompt composition, including workflow prompt pages, prompt node editing, ordered message roles, reusable modules, and rendering validation.
## Requirements
### Requirement: Workflow Prompt Pages
The system SHALL present prompt configuration grouped by actual application workflow.

#### Scenario: View workflow prompt tabs
- **WHEN** the user opens the prompt editor page
- **THEN** the system SHALL show separate workflow pages or tabs for workflows that use LLM prompts, including novel summarization, article summarization, and trigger scanning

#### Scenario: View workflow without prompt nodes
- **WHEN** a workflow does not use persistent LLM prompt nodes
- **THEN** the system SHALL clearly indicate that the workflow has no editable persistent prompt nodes instead of showing unrelated templates

### Requirement: Prompt Node Editing
The system SHALL allow the user to view and edit each prompt node that participates in a workflow.

#### Scenario: Select prompt node
- **WHEN** the user selects a prompt node inside a workflow
- **THEN** the system SHALL display that node's name, purpose, source key, editable message content, available variables, and save/reset state

#### Scenario: Save prompt node
- **WHEN** the user saves changes for a prompt node
- **THEN** the system SHALL persist the node configuration and subsequent tasks SHALL use the saved node configuration

#### Scenario: Reset prompt node
- **WHEN** the user resets a prompt node
- **THEN** the system SHALL restore that node to its default configuration without resetting unrelated workflow nodes

### Requirement: Prompt Message Roles And Ordering
The system SHALL allow each prompt node to contain an ordered sequence of prompt messages.

#### Scenario: Add role-based message
- **WHEN** the user adds a message to a prompt node
- **THEN** the system SHALL allow selecting the message role from system, user, and assistant

#### Scenario: Reorder prompt messages
- **WHEN** the user changes the order of messages in a prompt node
- **THEN** the system SHALL preserve the new order when saving and when running the workflow

#### Scenario: Render ordered messages
- **WHEN** a task uses a prompt node with multiple messages
- **THEN** the system SHALL send those messages to the LLM API in the saved order and with the saved roles

### Requirement: Prompt Modules
The system SHALL support reusable prompt modules that can be composed into prompt node messages.

#### Scenario: Create prompt module
- **WHEN** the user creates a prompt module with a name and content
- **THEN** the system SHALL make that module available for insertion or reference from prompt node messages

#### Scenario: Use prompt module in node
- **WHEN** a prompt node message references a prompt module
- **THEN** the system SHALL expand the module content during prompt rendering before sending the request to the LLM API

#### Scenario: Update referenced module
- **WHEN** the user updates a prompt module that is referenced by prompt nodes
- **THEN** subsequent task runs SHALL use the updated module content wherever it is referenced

### Requirement: Prompt Rendering Validation
The system SHALL validate prompt rendering before or during task start and report actionable errors.

#### Scenario: Missing prompt variable
- **WHEN** a prompt node references a variable that the workflow does not provide
- **THEN** the system SHALL reject the rendered prompt with a clear error identifying the missing variable and the prompt node

#### Scenario: Invalid module reference
- **WHEN** a prompt node references a module that does not exist
- **THEN** the system SHALL report a clear configuration error and SHALL NOT silently omit the module content

### Requirement: Trigger Scan Prompt Nodes
The system SHALL provide editable workflow prompt nodes for trigger scan stages that actually call an LLM, and SHALL clearly identify deterministic stages that do not use editable prompt content at runtime.

#### Scenario: View trigger scan prompt nodes
- **WHEN** the user opens the trigger scanning prompt workflow
- **THEN** the prompt editor SHALL show active LLM prompt nodes for precise scan and verification
- **AND** the prompt editor SHALL NOT present aggregation as an active LLM prompt node while runtime aggregation remains deterministic
- **AND** if aggregation prompt content is shown for compatibility, the prompt editor SHALL clearly state that it does not affect current trigger scan results
- **AND** the prompt editor SHALL NOT show a coarse scan prompt node

#### Scenario: Save trigger scan prompt node
- **WHEN** the user edits and saves an active trigger scan prompt node
- **THEN** subsequent trigger scan tasks SHALL use the saved messages for that LLM-backed stage

#### Scenario: Reset trigger scan prompt node
- **WHEN** the user resets one active trigger scan prompt node
- **THEN** the backend SHALL restore only that node to its default messages

### Requirement: Deferred LLM Aggregation Plan
The project SHALL retain a visible follow-up plan for a future LLM-backed trigger scan aggregation stage so the deterministic aggregation decision is not mistaken for permanent removal of the idea.

#### Scenario: Record future aggregation option
- **WHEN** this stability change is applied
- **THEN** the implementation tasks or documentation SHALL record that LLM aggregation via aggregation prompt is deferred to a future independent change
- **AND** the record SHALL mention expected follow-up topics including API cost, JSON parsing, fallback behavior, and UI disclosure

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
