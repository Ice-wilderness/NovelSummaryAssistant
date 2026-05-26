## ADDED Requirements

### Requirement: Summary Partial Warning Display

The WebUI workbench SHALL display article summary and custom summary `partial_failed` states as partial results with usable output and warnings, not as complete success or generic failure.

#### Scenario: Display partial article summary
- **WHEN** an article summary task finishes with status `partial_failed`
- **THEN** the article summary page SHALL show a partial failure state
- **AND** the page SHALL show that the generated final summary is available but may be incomplete
- **AND** the page SHALL show the failed section details returned by the backend

#### Scenario: Display partial custom summary
- **WHEN** a custom summary task finishes with status `partial_failed`
- **THEN** the custom summary page SHALL show a partial failure state
- **AND** the page SHALL keep the generated custom summary output visible
- **AND** the page SHALL show the failed source-file details returned by the backend

#### Scenario: Display summary partial status in shared task surfaces
- **WHEN** the global task status area or project history displays an article summary or custom summary task with status `partial_failed`
- **THEN** the WebUI SHALL label it as a partial result
- **AND** the WebUI SHALL NOT remap it to completed, success, failed, or cancelled

#### Scenario: Handle missing summary partial warnings
- **WHEN** a historical summary project has status `partial_failed` but no structured warning details
- **THEN** the WebUI SHALL display a generic partial-result warning
- **AND** the WebUI SHALL NOT fail to render the project page
