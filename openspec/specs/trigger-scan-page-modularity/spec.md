# trigger-scan-page-modularity Specification

## Purpose
Define the modular frontend boundaries and verification expectations for the trigger scan page after the split from a large page component.

## Requirements
### Requirement: Trigger scan page responsibilities are modularized
The WebUI SHALL split the trigger scan page implementation into cohesive frontend modules for profile management, scan configuration, report browsing, finding review, context display, and reusable display or filtering helpers while preserving the existing trigger scan workbench behavior.

#### Scenario: Page areas have focused modules
- **WHEN** a maintainer needs to update profile management, scan configuration, report display, finding review, or context viewing
- **THEN** the relevant frontend logic SHALL be discoverable in a focused trigger-scan module rather than only in the top-level page component

#### Scenario: Top-level page coordinates modules
- **WHEN** the trigger scan view renders after modularization
- **THEN** the top-level page SHALL coordinate shared state, task events, tab selection, and API calls while delegated modules render focused page areas

### Requirement: Trigger scan behavior is preserved during modularization
The modularization SHALL NOT change user-visible trigger scan fields, defaults, tabs, task controls, API request semantics, report warning display, spoiler controls, result filtering, review actions, or context lookup behavior.

#### Scenario: Existing tabs and controls remain available
- **WHEN** the user opens the trigger scan page after the split
- **THEN** the page SHALL still provide profile management, scan configuration, and scan results tabs with the same controls and labels as before

#### Scenario: Scan request payload remains compatible
- **WHEN** the user starts or resumes a trigger scan after the split
- **THEN** the frontend SHALL submit the same effective scan configuration fields and values to existing backend API endpoints

#### Scenario: Results remain reviewable
- **WHEN** the user views a completed, cancelled, failed, or partial trigger scan report after the split
- **THEN** the page SHALL preserve warning display, spoiler-level selection, finding filters, pagination, review status updates, notes, and context modal access

### Requirement: Frontend tests protect extracted behavior
The change SHALL add a minimal frontend test setup and focused tests for high-value extracted trigger scan helpers or components.

#### Scenario: Test script is available
- **WHEN** maintainers install frontend dependencies
- **THEN** the frontend package SHALL expose a repeatable test command for the new trigger scan frontend tests

#### Scenario: Extracted logic is covered
- **WHEN** helper logic for status display, report warnings, profile draft manipulation, filtering, or pagination is extracted
- **THEN** focused tests SHALL cover representative success and edge cases for that extracted behavior

#### Scenario: Build still verifies integration
- **WHEN** the modularization is complete
- **THEN** `npm run build` SHALL pass in addition to the new frontend test command
