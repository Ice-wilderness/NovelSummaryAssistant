## MODIFIED Requirements

### Requirement: Managed Project Deletion
The system SHALL allow users to delete an incorrect managed project from project history and remove WebUI-managed project files only when those files are proven to be owned by the managed project.

#### Scenario: Delete managed project
- **WHEN** the user deletes an existing managed project
- **THEN** the backend SHALL remove the project metadata directory and uploaded-file storage
- **AND** the backend SHALL remove the managed default export directory only if ownership metadata proves it belongs to that project

#### Scenario: Deleted project absent from history
- **WHEN** the user lists historical projects after deleting a managed project
- **THEN** the deleted project SHALL NOT appear in the historical project list

#### Scenario: Preserve unmanaged custom output
- **WHEN** a deleted project has a custom output directory outside the managed default export directory
- **THEN** the backend SHALL NOT delete the custom output directory

#### Scenario: Preserve output without ownership proof
- **WHEN** a deleted project's output directory lacks matching ownership metadata
- **THEN** the backend SHALL preserve that output directory
- **AND** the response SHALL provide enough information for the WebUI to inform the user that files were kept

#### Scenario: Delete missing project
- **WHEN** the user requests deletion for a project that does not exist
- **THEN** the backend SHALL return a clear validation error and SHALL NOT delete unrelated directories

### Requirement: Trigger Scan Artifacts On Project Deletion
The system SHALL handle trigger scan artifacts consistently with other managed outputs when a project is deleted, using the same ownership boundary as the parent output directory.

#### Scenario: Delete managed trigger scan output
- **WHEN** the user deletes a managed project whose trigger scan output is under an output directory with matching ownership metadata
- **THEN** the backend SHALL remove the trigger scan artifacts with the rest of that managed output directory

#### Scenario: Preserve unmanaged trigger scan output
- **WHEN** the user deletes a project whose custom output directory is outside the managed default export directory
- **THEN** the backend SHALL NOT delete that custom output directory or its trigger scan artifacts

#### Scenario: Preserve trigger scan output without ownership proof
- **WHEN** the user deletes a project whose trigger scan output exists under a directory without matching ownership metadata
- **THEN** the backend SHALL preserve those trigger scan artifacts

## ADDED Requirements

### Requirement: Managed Output Ownership Metadata
The system SHALL write ownership metadata for output directories it creates and manages so destructive cleanup can be bounded to project-owned paths.

#### Scenario: Create managed output directory
- **WHEN** the backend creates a managed output directory for a project
- **THEN** it SHALL write metadata identifying the project slug, output ownership, and managed directory purpose

#### Scenario: Verify ownership before recursive delete
- **WHEN** the backend is about to recursively delete an output directory as part of project deletion
- **THEN** it SHALL verify that ownership metadata matches the project being deleted
