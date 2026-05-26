## Purpose
Define partial-result semantics for summary workflows that can preserve usable output while clearly reporting incomplete input coverage.

## Requirements
### Requirement: Article Summary Partial Result
The system SHALL preserve usable article summary output while explicitly marking the task as partial when one or more selected article sections fail before the final summary is generated.

#### Scenario: Complete article summary succeeds
- **WHEN** all selected article section summaries are generated and the final article summary is generated
- **THEN** the article summary task SHALL finish with status `success`
- **AND** the task SHALL NOT report partial failure warnings

#### Scenario: Article section failure with final result
- **WHEN** one or more selected article sections fail but at least one section summary is available and the final article summary is generated from the available sections
- **THEN** the article summary task SHALL finish with status `partial_failed`
- **AND** the task SHALL preserve the generated final summary
- **AND** the task SHALL report which selected sections failed and warn that the final summary may be incomplete

#### Scenario: Article section failure without usable result
- **WHEN** all selected article sections fail or no section summary is available for the final summary stage
- **THEN** the article summary task SHALL finish with status `failed`
- **AND** the task SHALL NOT report a completed final summary

#### Scenario: Article final summary failure
- **WHEN** article section summaries are available but the final summary generation fails
- **THEN** the article summary task SHALL finish with status `failed`
- **AND** the task SHALL report the final summary failure instead of marking the task as `partial_failed`

### Requirement: Custom Summary Partial Input
The system SHALL preserve usable custom summary output while explicitly marking the task as partial when one or more selected source materials cannot be read before a successful final custom summary generation.

#### Scenario: Complete custom summary succeeds
- **WHEN** all selected custom summary source files are read and the custom summary output is generated
- **THEN** the custom summary task SHALL finish with status `success`
- **AND** the task SHALL NOT report partial failure warnings

#### Scenario: Custom material failure with generated result
- **WHEN** one or more selected custom summary source files cannot be read but at least one source file is read and the custom summary output is generated
- **THEN** the custom summary task SHALL finish with status `partial_failed`
- **AND** the task SHALL preserve the generated custom summary output
- **AND** the task SHALL report which source files failed and warn that the result may be incomplete

#### Scenario: Custom material failure without usable result
- **WHEN** all selected custom summary source files cannot be read or the custom summary API call fails without generated output
- **THEN** the custom summary task SHALL finish with status `failed`
- **AND** the task SHALL NOT report a successful or partial custom summary output

### Requirement: Summary Partial Metadata
The system SHALL expose summary partial failure details as structured task metadata instead of requiring the WebUI to parse runtime log text.

#### Scenario: Partial summary metadata is returned
- **WHEN** an article summary or custom summary task finishes with status `partial_failed`
- **THEN** the task record SHALL include warnings suitable for user display
- **AND** the task record SHALL include structured details for the failed sections or source files

#### Scenario: Old summary task has no partial metadata
- **WHEN** the WebUI loads an older summary task or project record without partial failure metadata
- **THEN** the system SHALL treat missing warnings and failed-unit details as empty
- **AND** the system SHALL continue to display the historical project without error
