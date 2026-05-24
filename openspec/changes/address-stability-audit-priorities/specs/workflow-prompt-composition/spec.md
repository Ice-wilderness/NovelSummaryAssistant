## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Deferred LLM Aggregation Plan
The project SHALL retain a visible follow-up plan for a future LLM-backed trigger scan aggregation stage so the deterministic aggregation decision is not mistaken for permanent removal of the idea.

#### Scenario: Record future aggregation option
- **WHEN** this stability change is applied
- **THEN** the implementation tasks or documentation SHALL record that LLM aggregation via aggregation prompt is deferred to a future independent change
- **AND** the record SHALL mention expected follow-up topics including API cost, JSON parsing, fallback behavior, and UI disclosure
