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
