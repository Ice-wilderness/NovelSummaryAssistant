## ADDED Requirements

### Requirement: Uploaded File Inputs
The system SHALL allow users to provide workflow input files through browser file upload instead of requiring local filesystem paths.

#### Scenario: Upload single file input
- **WHEN** the user selects a single text file for a single-file workflow
- **THEN** the backend SHALL store the file in the managed project workspace and return an uploaded-file reference usable by task start APIs

#### Scenario: Upload multiple file inputs
- **WHEN** the user selects multiple text files for a multi-file workflow
- **THEN** the backend SHALL store all accepted files in the managed project workspace and return ordered uploaded-file references

#### Scenario: Reject unsupported upload
- **WHEN** the user uploads a file type or size that is not allowed
- **THEN** the backend SHALL reject the upload with an actionable validation error and SHALL NOT start a task with that file

### Requirement: Uploaded File Task Resolution
The system SHALL resolve uploaded-file references to backend-local files before invoking existing workflow logic.

#### Scenario: Start task from uploaded files
- **WHEN** the WebUI starts a workflow using uploaded-file references
- **THEN** the backend SHALL resolve those references to files in the managed project workspace before calling the task runner

#### Scenario: Missing uploaded file reference
- **WHEN** a task request references an uploaded file that does not exist
- **THEN** the backend SHALL reject the request with a clear validation error and SHALL NOT start a background task

### Requirement: Path Drag Workflow Removal
The system SHALL stop depending on drag-and-drop local path extraction for file inputs.

#### Scenario: View file input controls
- **WHEN** the user views a workflow file input
- **THEN** the WebUI SHALL show file upload controls instead of a path input that expects dragged local filesystem paths

#### Scenario: Remove obsolete path diagnostics
- **WHEN** the upload workflow is implemented
- **THEN** temporary path-drag diagnostics and obsolete path resolution code SHALL be removed or limited to explicit custom-directory validation
