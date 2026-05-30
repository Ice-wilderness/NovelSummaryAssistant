# studio-workbench-experience Specification

## Purpose
Define the PC-first Studio Workbench experience, including information architecture, visual system, motion polish, guided interactions, and desktop verification expectations for the modernized WebUI.
## Requirements
### Requirement: PC-First Studio Workbench
The WebUI SHALL provide a PC-first studio workbench experience that organizes existing workflows around project context, current task stage, current-step actions, and live task feedback.

#### Scenario: Open studio workbench on desktop
- **WHEN** the user opens the local WebUI on a desktop-width browser
- **THEN** the workbench SHALL show a studio layout with visible workflow navigation, project or workflow context, primary work surface, current-step action area, and live task feedback area
- **AND** the layout SHALL be optimized for PC desktop use rather than mobile-first navigation

#### Scenario: Preserve existing workflow access
- **WHEN** the studio workbench is displayed
- **THEN** the user SHALL be able to reach novel summarization, article summarization, custom summarization, chapter splitting, trigger scanning, prompt editing, API configuration, and logs

#### Scenario: Avoid demo-only implementation
- **WHEN** the studio workbench is implemented
- **THEN** the implementation SHALL adapt the design direction to the real project workflows and SHALL NOT reproduce static demo content as production UI data

### Requirement: Studio Information Architecture
The WebUI SHALL present workflow information in a structure that keeps the current project, current workflow, current stage, and next actions understandable at a glance.

#### Scenario: View project context
- **WHEN** a workflow with managed projects is open
- **THEN** the workbench SHALL show the selected project identity, project history or context index, output target status, and recoverable warnings or repair state when available

#### Scenario: View current task stage
- **WHEN** a long-running task is pending, running, paused, canceling, terminal, or interrupted
- **THEN** the workbench SHALL show the task state and stage progress in a prominent area without requiring the user to open logs

#### Scenario: View next actions
- **WHEN** the user opens a workflow page
- **THEN** the workbench SHALL surface the most relevant next actions for that workflow state, such as upload, save project, preview split, start task, continue, repair, review findings, export report, or open output directory

### Requirement: Modern Visual System
The WebUI SHALL use a cohesive modern visual system that improves hierarchy, polish, readability, and comfort for long PC work sessions.

#### Scenario: Render modern surfaces
- **WHEN** the user views any redesigned workbench page
- **THEN** the page SHALL use consistent typography, spacing, color, panel treatment, focus state, status labels, and icon usage
- **AND** the page SHALL avoid a plain three-column reskin that preserves the old information hierarchy unchanged

#### Scenario: Show dense information comfortably
- **WHEN** a page contains many controls, logs, results, or configuration fields
- **THEN** the visual system SHALL group related information into readable sections with clear hierarchy and sufficient spacing
- **AND** long names, paths, warnings, and log lines SHALL remain readable or expandable

#### Scenario: Maintain status clarity
- **WHEN** the workbench displays success, running, paused, cancelled, partial failure, failure, interrupted, warning, or repair states
- **THEN** those states SHALL use visually distinct treatments that remain understandable without relying on color alone

### Requirement: Motion And Interaction Polish
The WebUI SHALL use motion and interaction feedback to make workflow changes feel responsive, comfortable, and premium while preserving task clarity.

#### Scenario: Animate workflow transitions
- **WHEN** the user switches primary workflow views or current-step panels
- **THEN** the workbench SHALL use a smooth transition or animated state change that preserves orientation and does not hide the destination content

#### Scenario: Animate task progress changes
- **WHEN** stage progress, task state, or logs update while a task is running
- **THEN** the workbench SHALL provide visible feedback such as subtle progress motion, state transition, or log insertion animation
- **AND** the animation SHALL NOT misrepresent completion or hide warnings and errors

#### Scenario: Provide input feedback
- **WHEN** the user hovers, focuses, expands, collapses, drags, uploads, saves, starts, pauses, cancels, repairs, reviews, or exports
- **THEN** the control SHALL provide immediate visual feedback through motion, focus styling, pressed state, loading state, or status change

### Requirement: Guided Workflow Interactions
The WebUI SHALL guide users through complex workflows with contextual, complete, and action-oriented guidance.

#### Scenario: Guide upload-to-summary flow
- **WHEN** the user opens the novel summary workflow without a ready project
- **THEN** the page SHALL guide the user from source upload or project import through split preview, project save, API selection, task configuration, and task start

#### Scenario: Guide task recovery flow
- **WHEN** the selected project has reconciliation warnings, missing outputs, invalid output directory, interrupted task state, or repairable issues
- **THEN** the page SHALL present the issue near the relevant project or output context with clear next actions and required confirmations

#### Scenario: Guide trigger scan review
- **WHEN** the user opens trigger scan results
- **THEN** the page SHALL guide the user through report selection, severity/confidence filtering, spoiler level review, finding confirmation, false-positive marking, note editing, context inspection, and export

### Requirement: External Frontend Enhancements
The WebUI MAY add external frontend libraries, extensions, or plugins to improve visual quality, animation, accessibility, or interaction comfort, but such dependencies MUST remain compatible with the local WebUI build and testing workflow.

#### Scenario: Add animation or UI dependency
- **WHEN** a new frontend dependency is introduced for studio workbench implementation
- **THEN** the dependency SHALL have a clear role such as animation, accessible primitives, tooltips, dialogs, scroll areas, layout utilities, or interaction polish
- **AND** `npm run build` or equivalent frontend build verification SHALL remain passing

#### Scenario: Avoid dependency-driven feature loss
- **WHEN** external libraries are used for redesigned controls
- **THEN** existing workflow behavior, validation, task control, error display, logging, and project recovery behavior SHALL remain available

### Requirement: Desktop Verification
The redesigned WebUI SHALL be verified primarily on PC desktop-width viewports.

#### Scenario: Verify desktop layout
- **WHEN** a redesigned page is completed
- **THEN** it SHALL be checked at a desktop-width viewport for non-overlapping layout, readable text, visible key actions, and usable logs or status feedback

#### Scenario: Treat mobile as non-primary
- **WHEN** implementation trade-offs arise between desktop workflow quality and mobile layout completeness
- **THEN** the implementation SHALL prioritize the PC desktop workflow while keeping critical content reachable in narrower browser widths where feasible
