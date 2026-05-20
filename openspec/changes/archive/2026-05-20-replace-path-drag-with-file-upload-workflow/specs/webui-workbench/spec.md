## ADDED Requirements

### Requirement: Upload-Based Workflow Controls
The WebUI workbench SHALL present upload controls for workflow file inputs and managed output controls for generated files.

#### Scenario: Upload files on workflow page
- **WHEN** the user opens a workflow that consumes local text files
- **THEN** the page SHALL provide file upload controls with accepted file guidance instead of requiring the user to drag or type local file paths

#### Scenario: Configure project output
- **WHEN** the user opens a workflow that produces files
- **THEN** the page SHALL show the project name, default export location, custom output override, and open-directory action clearly enough to understand where files will be written

#### Scenario: Display uploaded file list
- **WHEN** the user selects or uploads files
- **THEN** the page SHALL display the uploaded file names and allow removing files before task start

### Requirement: Historical Project Recovery Controls
The WebUI workbench SHALL provide controls for selecting historical projects and restoring unfinished work.

#### Scenario: Show historical projects
- **WHEN** the user opens a workflow page with historical projects
- **THEN** the page SHALL provide a history selector showing recent project names, workflow type, latest task status, and update time

#### Scenario: Restore selected project
- **WHEN** the user selects a historical project
- **THEN** the page SHALL restore the project name, uploaded file list, output target, and available resume/start controls for that project

#### Scenario: No historical projects
- **WHEN** no historical projects exist for the workflow
- **THEN** the page SHALL keep the upload-first workflow usable and SHALL show an unobtrusive empty history state
