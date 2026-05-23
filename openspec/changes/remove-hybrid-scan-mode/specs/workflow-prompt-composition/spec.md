## MODIFIED Requirements

### Requirement: Trigger Scan Prompt Nodes
The system SHALL provide editable workflow prompt nodes for every AI-assisted trigger scan stage that remains active.

#### Scenario: View trigger scan prompt nodes
- **WHEN** the user opens the trigger scanning prompt workflow
- **THEN** the prompt editor SHALL show nodes for precise scan, verification, and aggregation
- **AND** the prompt editor SHALL NOT show a coarse scan prompt node

#### Scenario: Save trigger scan prompt node
- **WHEN** the user edits and saves a trigger scan prompt node
- **THEN** subsequent trigger scan tasks SHALL use the saved messages for that stage

#### Scenario: Reset trigger scan prompt node
- **WHEN** the user resets one trigger scan prompt node
- **THEN** the backend SHALL restore only that node to its default messages
