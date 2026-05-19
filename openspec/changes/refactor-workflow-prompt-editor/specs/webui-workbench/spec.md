## ADDED Requirements

### Requirement: Page Guidance
The WebUI workbench SHALL provide concise guidance for every current page so users can understand each workflow, button, configuration item, and module without leaving the page.

#### Scenario: View page guidance
- **WHEN** the user opens any primary workbench page
- **THEN** the page SHALL include concise guidance explaining the page purpose and the meaning of its main controls

#### Scenario: View field guidance
- **WHEN** the user views a configuration field whose meaning affects task behavior
- **THEN** the field SHALL provide a short label, hint, tooltip, or nearby help text explaining its purpose

#### Scenario: View action guidance
- **WHEN** the user hovers, focuses, or reads a button that starts, saves, resets, deletes, loads, pauses, resumes, or cancels work
- **THEN** the action SHALL be named or described clearly enough to communicate its effect

### Requirement: Prompt Editor Workbench
The WebUI workbench SHALL make the prompt editor usable for workflow-level prompt composition.

#### Scenario: Navigate prompt editor sections
- **WHEN** the user opens the prompt editor
- **THEN** the workbench SHALL provide a clear way to move between workflow selection, prompt node editing, message editing, and module management

#### Scenario: Understand prompt modules
- **WHEN** the user views prompt modules
- **THEN** the workbench SHALL explain where modules can be used and whether changes affect referenced prompt nodes

#### Scenario: Track unsaved prompt edits
- **WHEN** the user changes prompt node messages or modules without saving
- **THEN** the workbench SHALL show an unsaved state and SHALL prevent the change from being mistaken for an active saved configuration

### Requirement: Guidance Responsive Layout
The WebUI workbench SHALL keep page guidance readable and controls usable on common desktop and tablet browser widths.

#### Scenario: Resize guided page
- **WHEN** the browser viewport changes between desktop and tablet widths
- **THEN** guidance text, form controls, prompt messages, module lists, task controls, and logs SHALL remain visible or reachable without overlapping content
