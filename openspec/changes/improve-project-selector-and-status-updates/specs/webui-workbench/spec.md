## MODIFIED Requirements

### Requirement: Historical Project Recovery Controls
The WebUI workbench SHALL provide controls for selecting historical projects, restoring unfinished work, starting a fresh project, deleting incorrect projects, and keeping displayed project status current after task completion.

#### Scenario: Show historical projects
- **WHEN** the user opens a workflow page with historical projects
- **THEN** the page SHALL provide a history control showing recent project names, workflow type, latest task status as a leading visual label, and update time without appending status text after the project name

#### Scenario: Restore selected project
- **WHEN** the user selects a historical project
- **THEN** the page SHALL restore the project name, uploaded file list, output target, and available resume/start controls for that project

#### Scenario: Start new project
- **WHEN** the user activates the new-project action after a historical project has been selected
- **THEN** the page SHALL clear the selected project context and keep upload-first controls ready for a fresh project

#### Scenario: New project outside history selector
- **WHEN** the user opens the historical project control
- **THEN** the new-project action SHALL be presented separately from historical project options

#### Scenario: Refresh project status after task completion
- **WHEN** a task started from a managed project reaches a terminal state
- **THEN** the workflow page SHALL refresh the affected project history and show the latest task status without requiring a browser refresh

#### Scenario: Delete historical project
- **WHEN** the user confirms deletion of a historical project
- **THEN** the page SHALL request project deletion, remove the project from history, and clear the current project context if the deleted project was selected

#### Scenario: No historical projects
- **WHEN** no historical projects exist for the workflow
- **THEN** the page SHALL keep the upload-first workflow usable and SHALL show an unobtrusive empty history state

### Requirement: Upload-Based Workflow Controls
The WebUI workbench SHALL present upload controls for workflow file inputs and managed output controls for generated files.

#### Scenario: Upload files on workflow page
- **WHEN** the user opens a workflow that consumes local text files
- **THEN** the page SHALL provide file upload controls with accepted file guidance instead of requiring the user to drag or type local file paths

#### Scenario: Configure project output
- **WHEN** the user opens a workflow that produces files
- **THEN** the page SHALL show the project name, effective output directory, browse action, and open-directory action clearly enough to understand where files will be written

#### Scenario: Display effective output priority
- **WHEN** the workflow page displays an output directory for a managed project
- **THEN** the displayed directory SHALL reflect the priority of project-level custom directory, user-level default export directory, then current fallback default export directory

#### Scenario: Display uploaded file list
- **WHEN** the user selects or uploads files
- **THEN** the page SHALL display the uploaded file names and allow removing files before task start
