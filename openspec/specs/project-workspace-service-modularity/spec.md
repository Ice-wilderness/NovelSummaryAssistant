## Purpose

Define the modular internal structure and compatibility boundary for project workspace services while preserving existing WebUI project behavior.

## Requirements

### Requirement: Project workspace public facade remains stable

系统 SHALL keep `webui_backend.project_workspace` as the stable public import boundary for project workspace models, constants, helper functions, and `ProjectWorkspaceService` while internal implementation code is modularized.

#### Scenario: Existing imports continue to work

- **WHEN** backend routes, tests, or workflow services import existing project workspace symbols from `webui_backend.project_workspace`
- **THEN** those imports SHALL continue to resolve without requiring callers to import from newly introduced internal helper modules

#### Scenario: Service construction remains compatible

- **WHEN** code constructs `ProjectWorkspaceService` with the existing constructor arguments
- **THEN** the service SHALL initialize with the same path injection semantics as before the split

### Requirement: Workspace service responsibilities are modularized

系统 SHALL split project workspace implementation details into cohesive internal modules for responsibilities such as metadata persistence, uploaded-file handling, output directory ownership, import recognition, progress scanning, and local directory opening.

#### Scenario: Internal modules have clear ownership

- **WHEN** a maintainer needs to modify one project workspace responsibility after the split
- **THEN** the relevant logic SHALL be discoverable in an internal module focused on that responsibility rather than only inside the main facade file

#### Scenario: Facade coordinates internal helpers

- **WHEN** project workspace operations require multiple responsibilities such as saving metadata and resolving output directories
- **THEN** `ProjectWorkspaceService` SHALL coordinate the internal helpers while preserving the existing external method contract

### Requirement: Project workspace behavior is preserved

系统 SHALL treat the modularization as a no-behavior-change refactor for managed projects, uploads, output directories, imports, deletion protection, progress recognition, and local directory opening.

#### Scenario: Existing project workspace tests remain valid

- **WHEN** the project workspace test suite runs after the split
- **THEN** existing assertions for upload ordering, metadata compatibility, output ownership, output migration, project deletion, legacy import recognition, progress scanning, and directory opening SHALL continue to pass

#### Scenario: Existing API behavior remains compatible

- **WHEN** the WebUI backend API uses project workspace operations through existing routes
- **THEN** request payloads, response shapes, status-code semantics, and effective filesystem side effects SHALL remain compatible with the behavior before the split

### Requirement: No data migration or dependency change is introduced

系统 SHALL NOT require users to migrate existing workspace metadata, uploaded files, export directories, trigger scan artifacts, or configuration files as a result of the project workspace modularization.

#### Scenario: Existing local data remains readable

- **WHEN** the backend loads project metadata, uploaded-file references, managed output ownership metadata, imported project outputs, or trigger scan artifacts created before the split
- **THEN** it SHALL read them using the same persisted schema and filesystem layout

#### Scenario: Dependency footprint remains unchanged

- **WHEN** the change is implemented
- **THEN** it SHALL NOT add runtime or frontend dependencies solely to support the project workspace service split
