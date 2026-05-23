## Purpose
Define the stage progress bar visualization that shows workflow progress across all stages for novel summary and trigger scan tasks.

## Requirements
### Requirement: Stage Progress Bar Component
The WebUI SHALL display a stage progress bar that covers all stages of the current workflow when the user enters a project page.

#### Scenario: Show progress bar on project load
- **WHEN** the user opens a novel summary or trigger scan page with a selected project
- **THEN** the WebUI SHALL display a horizontal stage progress bar showing all workflow stages with their labels, completion counts, and status (completed, running, pending)
- **AND** the progress bar SHALL appear above the task control buttons and log panel

#### Scenario: Highlight current stage
- **WHEN** a task is running
- **THEN** the progress bar SHALL visually distinguish the current stage from completed and pending stages using distinct colors or styles
- **AND** the current stage SHALL show an animated or pulsing indicator

#### Scenario: Show completed and total per stage
- **WHEN** the progress bar is displayed
- **THEN** each stage segment SHALL show the completed count and total count when available
- **AND** stages with no total (indeterminate) SHALL display a waiting indicator

#### Scenario: Initialize from project progress
- **WHEN** the user enters a project page and no task is running
- **THEN** the WebUI SHALL request the project's file-system-based progress and render the stage progress bar with the most recent known state
- **AND** completed stages SHALL show a completion check mark

#### Scenario: Real-time update during task execution
- **WHEN** a task is running and the backend emits a stage progress event with a stages array
- **THEN** the WebUI SHALL replace the progress bar state with the incoming stages array
- **AND** the completed count for the current stage SHALL increment without full bar re-render flicker

#### Scenario: Fall back to static progress after task ends
- **WHEN** a task reaches a terminal state and the SSE connection closes
- **THEN** the WebUI SHALL request the file-system-based progress and render the final completed state

#### Scenario: No project selected
- **WHEN** no project is selected on the page
- **THEN** the progress bar SHALL be hidden or show an empty placeholder state

### Requirement: Unified Stage Progress Data Format
The stage progress bar SHALL consume a unified data format shared across novel summary and trigger scan workflows.

#### Scenario: Parse stages array from event
- **WHEN** the backend emits a progress event with a `data.stages` array
- **THEN** each stage object SHALL be parsed as containing `id` (string), `label` (string), `completed` (number), `total` (number or null), and `status` (one of `completed`, `running`, `pending`)

#### Scenario: Parse current stage from event
- **WHEN** the backend emits a progress event with `data.current_stage`
- **THEN** the WebUI SHALL use it to identify which stage is actively running for the animated indicator
