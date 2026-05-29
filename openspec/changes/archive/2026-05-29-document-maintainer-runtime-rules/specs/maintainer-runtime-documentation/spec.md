## ADDED Requirements

### Requirement: Maintainer Documentation Entry
The project SHALL provide a maintainer-focused README entry that points to current development, validation, OpenSpec, runtime directory, and troubleshooting documentation.

#### Scenario: Maintainer finds validation commands
- **WHEN** a maintainer reads the README
- **THEN** the README SHALL list or link to the standard backend, frontend, build, and OpenSpec validation commands

#### Scenario: Maintainer finds deeper runtime notes
- **WHEN** a maintainer needs details about task states, runtime files, or local path behavior
- **THEN** the README SHALL link to the dedicated runtime behavior documentation

### Requirement: Runtime Behavior Notes
The project SHALL document current runtime behavior rules that are important for safe maintenance.

#### Scenario: Task state rules are documented
- **WHEN** a maintainer reads the runtime behavior notes
- **THEN** the notes SHALL describe the meanings and maintenance boundaries for terminal task states including `success`, `failed`, `cancelled`, `partial_failed`, and `interrupted`

#### Scenario: Event stream rules are documented
- **WHEN** a maintainer reads the runtime behavior notes
- **THEN** the notes SHALL describe task event IDs, replay cursors, `Last-Event-ID`, replay gaps, heartbeat behavior, retention limits, and the status-query fallback boundary

#### Scenario: Repair and local boundary rules are documented
- **WHEN** a maintainer reads the runtime behavior notes
- **THEN** the notes SHALL describe project reconcile/repair boundaries, configuration recovery warnings, strict versus compat output directory behavior, and local picker/open-directory constraints

### Requirement: Spec To Test Mapping
The project SHALL provide a maintained mapping from high-value OpenSpec capabilities to verification commands and representative test files.

#### Scenario: Maintainer traces a capability to tests
- **WHEN** a maintainer looks up a high-value capability in the mapping
- **THEN** the mapping SHALL identify the relevant spec path, representative backend or frontend test files, and the recommended focused or full verification command

#### Scenario: Mapping scope is explicit
- **WHEN** a maintainer reads the mapping
- **THEN** the mapping SHALL state that it is a navigation aid for key coverage and does not replace running the documented test suite

### Requirement: Archived Changes Index
The project SHALL provide an index for notable archived OpenSpec changes.

#### Scenario: Maintainer finds archived change context
- **WHEN** a maintainer needs context for a recently archived stability or maintenance change
- **THEN** the index SHALL list the archived change name, its topic, related current spec or docs location, and where to inspect detailed proposal/design/tasks records

#### Scenario: Index avoids duplicating source artifacts
- **WHEN** a maintainer reads the archived changes index
- **THEN** the index SHALL summarize navigation metadata without replacing the archived change files as the authoritative historical record

### Requirement: Documentation-Only Boundary
The maintainer runtime documentation change SHALL NOT alter application behavior, public API contracts, runtime file formats, or dependency requirements.

#### Scenario: Implementation remains documentation-only
- **WHEN** the change is implemented
- **THEN** modified files SHALL be limited to README, docs, and OpenSpec artifacts unless a later approved change explicitly expands the scope
