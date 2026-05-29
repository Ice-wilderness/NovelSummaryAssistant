## ADDED Requirements

### Requirement: API Attempt And Parse Retry Semantics
The trigger scan workflow SHALL keep API request total attempts distinct from trigger scan response parsing retries.

#### Scenario: Apply API total attempts per request
- **WHEN** the trigger scan workflow sends an LLM API request
- **THEN** the configured API retry field SHALL be interpreted as the maximum total attempts for that API request, including the initial attempt
- **AND** logs or diagnostics for the request SHALL use total-attempt wording rather than implying the value is only additional retries

#### Scenario: Retry parse failures independently
- **WHEN** a trigger scan LLM response cannot be parsed into the required scan JSON shape
- **THEN** the workflow SHALL use an independent parse retry concept such as `parse_retries` or equivalent internal naming
- **AND** parse retries SHALL NOT change the saved API configuration retry value
- **AND** any parse retry that sends another API request SHALL still apply the API configuration's total-attempt limit for that individual request

#### Scenario: Report exhausted retry cause
- **WHEN** a trigger scan unit fails after exhausting API attempts, parse retries, or both
- **THEN** the task failure, preserved partial report warning, or diagnostic output SHALL identify whether the failure came from API request attempts, scan response parsing, or both
- **AND** the message SHALL include enough attempt-count context for a maintainer or user to understand the maximum calls attempted for that unit
