## MODIFIED Requirements

### Requirement: Project History API
The backend SHALL expose API operations for listing, loading, deleting, and managing managed project history.

#### Scenario: List project history
- **WHEN** the WebUI requests historical projects
- **THEN** the backend SHALL return project summaries with project identity, workflow type, uploaded file summary, output target, latest task status, and update timestamp

#### Scenario: Load project details
- **WHEN** the WebUI requests details for a historical project
- **THEN** the backend SHALL return restorable project state including uploaded-file references, output settings, and resumable task context

#### Scenario: Delete project history
- **WHEN** the WebUI requests deletion for a historical project
- **THEN** the backend SHALL delete that managed project and return a success response suitable for refreshing the project list

#### Scenario: Project history unavailable
- **WHEN** a requested historical project does not exist or is missing required metadata
- **THEN** the backend SHALL return a clear validation error and SHALL NOT fabricate project state

### Requirement: Managed Output Targets
The backend task API SHALL accept managed output targets based on project name, optional project-level custom output directory, and user-level default export directory.

#### Scenario: Start workflow with project-level custom output
- **WHEN** a task request includes a valid project-level custom output directory
- **THEN** the backend SHALL validate and use that directory as the task output target

#### Scenario: Start workflow with user-level default output
- **WHEN** a task request omits a project-level custom output directory and a valid user-level default export directory is configured
- **THEN** the backend SHALL resolve the output target under the user-level default export directory for the request's project name

#### Scenario: Start workflow with fallback managed output
- **WHEN** a task request omits a project-level custom output directory and no valid user-level default export directory is configured
- **THEN** the backend SHALL resolve the output target to the current managed fallback export directory for the request's project name

### Requirement: API Failure Diagnostics
The backend task runtime SHALL write one readable diagnostic file for each failed API attempt.

#### Scenario: Log failed API attempt
- **WHEN** an API attempt fails due to request error, HTTP error, response parsing error, invalid response shape, or minimum output length validation
- **THEN** the backend SHALL write a single formatted JSON diagnostic file for that failed attempt in a dedicated API failure-log directory

#### Scenario: Avoid combined failure log
- **WHEN** multiple API attempts fail during a task
- **THEN** the backend SHALL create separate formatted JSON files for each failure instead of appending all failures into one JSONL-style file

#### Scenario: Redact sensitive diagnostic fields
- **WHEN** the backend writes an API failure diagnostic file
- **THEN** the file SHALL omit or redact API keys, authorization headers, and other secret credentials

#### Scenario: Include useful diagnostic context
- **WHEN** the backend writes an API failure diagnostic file
- **THEN** the file SHALL include task stage, project or chapter context when available, API display name, attempt number, error type, status code when available, traceback or error summary, and response content when available

### Requirement: Minimum Output Length Validation
The backend task runtime SHALL reject API outputs whose visible content is shorter than the configured minimum output character count.

#### Scenario: Accept output meeting minimum length
- **WHEN** the configured minimum output character count is zero or the API output visible content length is greater than or equal to the configured value
- **THEN** the backend SHALL accept the output for the normal task pipeline

#### Scenario: Reject output below minimum length
- **WHEN** the API output visible content length is below the configured minimum output character count
- **THEN** the backend SHALL discard the output, write an API failure diagnostic file, and retry according to the existing retry policy

#### Scenario: Exhaust retries after short outputs
- **WHEN** all retry attempts produce output below the configured minimum output character count
- **THEN** the backend SHALL fail that unit with a clear error and SHALL NOT write the too-short output as a completed summary
