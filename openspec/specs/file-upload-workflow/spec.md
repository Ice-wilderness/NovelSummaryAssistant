## Purpose
Define the upload-based file input workflow that replaces browser local path extraction for text-file workflows.

## Requirements

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

### Requirement: Client Upload Size Preflight
The WebUI SHALL reject text files that exceed the backend single-file upload size limit before reading their contents into browser memory.

#### Scenario: Reject oversized managed project upload
- **WHEN** the user selects a file larger than 100 MB in a managed workflow upload control
- **THEN** the WebUI SHALL reject the file before calling `arrayBuffer()`
- **AND** the WebUI SHALL display an actionable upload-size error
- **AND** the WebUI SHALL NOT submit that file to the backend upload API

#### Scenario: Reject oversized novel source split upload
- **WHEN** the user selects a novel source file larger than 100 MB for split preview or split-and-ingest
- **THEN** the WebUI SHALL reject the file before reading it into memory
- **AND** the WebUI SHALL display an actionable upload-size error
- **AND** the WebUI SHALL NOT retain that source file for preview or splitting

#### Scenario: Accept file within upload limit
- **WHEN** the user selects a text file whose size is less than or equal to 100 MB
- **THEN** the WebUI SHALL continue using the existing text decoding and upload or preview workflow

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
