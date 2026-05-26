# logic-utils-modularity Specification

## Purpose
Defines the compatibility and modularity requirements for the split `logic.utils` facade and its focused helper modules.

## Requirements
### Requirement: Compatible Logic Utils Facade

The system SHALL preserve `logic.utils` as the stable import facade for the helper symbols that existed before the split.

#### Scenario: Existing imports continue to work

- **WHEN** code imports existing helper symbols from `logic.utils`
- **THEN** those imports MUST resolve without requiring callers to migrate to the new focused modules

#### Scenario: Module import style continues to work

- **WHEN** code imports `utils` via `from logic import utils`
- **THEN** existing attribute access for moved helper symbols MUST continue to work

### Requirement: Focused Internal Helper Modules

The system SHALL move `logic/utils.py` responsibilities into focused internal modules grouped by stable responsibilities rather than by incidental source order.

#### Scenario: Summary output helpers are isolated

- **WHEN** maintainers inspect summary output path and filename helpers
- **THEN** those helpers MUST be grouped in a focused module separate from unrelated prompt, API logging, batching, and chapter writing logic

#### Scenario: API diagnostic logging helpers are isolated

- **WHEN** maintainers inspect API task/failure logging and cleanup helpers
- **THEN** those helpers MUST be grouped in a focused module that preserves existing log paths, redaction behavior, async locking, and retention behavior

#### Scenario: Chapter and batch helpers are isolated

- **WHEN** maintainers inspect chapter naming, sorting, batch allocation, or chapter writing helpers
- **THEN** those helpers MUST be grouped by responsibility so summary workflows, splitters, and trigger scan code do not depend on unrelated utility sections

### Requirement: Behavior-Preserving Refactor

The system SHALL preserve existing runtime behavior while splitting `logic/utils.py`.

#### Scenario: Generated paths and filenames remain stable

- **WHEN** summary outputs, cache directories, API log files, failure log directories, final summary paths, or chapter files are generated
- **THEN** their paths, names, formats, and compatibility rules MUST remain unchanged

#### Scenario: Workflow helper semantics remain stable

- **WHEN** workflows use moved helpers for prompt loading, file reading, tag extraction, chapter sorting, chapter range parsing, batch allocation, pause checks, or chapter writing
- **THEN** their observable behavior MUST match the pre-split behavior

#### Scenario: No unrelated fixes are included

- **WHEN** the split is implemented
- **THEN** it MUST NOT change article partial success behavior, state/output reconcile behavior, raw regex protection, preview/runtime split consistency, WebUI API contracts, or frontend behavior

### Requirement: Incremental Verification

The system SHALL verify each split boundary with focused checks before the final full regression run.

#### Scenario: Boundary-specific tests are run

- **WHEN** a utility responsibility is moved to a focused module
- **THEN** the most relevant existing tests for that responsibility MUST be run before moving to the next boundary

#### Scenario: Final regression is run

- **WHEN** all planned utility boundaries have been split and cleanup is complete
- **THEN** the full Python test suite MUST pass
