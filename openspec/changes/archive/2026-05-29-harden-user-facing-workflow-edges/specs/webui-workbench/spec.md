## ADDED Requirements

### Requirement: Task Subscription Cache Cleanup
The WebUI workbench SHALL bound per-task task-event subscription caches after terminal states are made visible.

#### Scenario: Clear task replay cache after terminal refresh
- **WHEN** a task event stream receives or recovers a terminal state for `success`, `failed`, `cancelled`, `partial_failed`, or `interrupted`
- **THEN** the WebUI SHALL refresh the latest task status from the backend before completing terminal handling
- **AND** after that terminal refresh succeeds or is otherwise handled, the WebUI SHALL clear the replay cursor and processed event id set for that task
- **AND** the cleanup SHALL NOT clear replay state for other active tasks

#### Scenario: Preserve replay cache while task is active
- **WHEN** a task event stream disconnects or reconnects before the task reaches a terminal state
- **THEN** the WebUI SHALL preserve that task's latest replay cursor and processed event id set
- **AND** reconnect behavior SHALL continue using the latest processed event id to avoid missing retained events

### Requirement: Core Workflow State Baseline
The WebUI workbench SHALL preserve core user-visible workflow states that are high risk during page refactors.

#### Scenario: Display summary task terminal states
- **WHEN** a novel summary, article summary, or custom summary task reaches `success`, `failed`, `cancelled`, or `partial_failed`
- **THEN** the relevant workflow page and shared task status surface SHALL display the matching terminal state without remapping it to a different outcome
- **AND** available warnings, errors, or partial-result details SHALL remain visible
- **AND** task actions invalid for the terminal state SHALL be disabled or hidden

#### Scenario: Display splitter task state
- **WHEN** a chapter splitter task starts, fails, succeeds, or is cancelled
- **THEN** the splitter-related page surface SHALL display the current task state
- **AND** the start action SHALL be disabled while the splitter task is running
- **AND** terminal handling SHALL refresh project state when the task can affect managed project files

#### Scenario: Display trigger scan report states
- **WHEN** the user views trigger scan report history or report details containing `completed`, `partial_failed`, legacy-compatible, or warning-bearing reports
- **THEN** the WebUI SHALL display the corresponding status and warning text
- **AND** the WebUI SHALL keep available findings or events visible when the report is partially usable

#### Scenario: Refresh managed project state after terminal task
- **WHEN** a task started from a managed project reaches a terminal state
- **THEN** the workflow page SHALL refresh affected project details or history
- **AND** the latest project status SHALL be visible without requiring a browser refresh
