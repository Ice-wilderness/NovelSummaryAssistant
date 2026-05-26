## ADDED Requirements

### Requirement: Readable API Client Error Handling
The WebUI API client SHALL preserve HTTP status information and provide readable error details for both JSON and non-JSON failed responses.

#### Scenario: Failed JSON response
- **WHEN** an API request receives a non-2xx response with a JSON body containing `detail`
- **THEN** the WebUI API client SHALL throw an `ApiError` with the response status
- **AND** the error message or detail SHALL include the backend-provided detail

#### Scenario: Failed non-JSON response
- **WHEN** an API request receives a non-2xx response with a plain text, HTML, empty, or otherwise non-JSON body
- **THEN** the WebUI API client SHALL throw an `ApiError` with the response status
- **AND** the error message or detail SHALL include the response status text or a short body preview
- **AND** the WebUI API client SHALL NOT expose a raw JSON parsing exception to the page

### Requirement: Unified Splitter Task API Usage
The WebUI workbench SHALL start chapter splitter tasks through the shared API client rather than page-local `fetch` error handling.

#### Scenario: Start splitter task from novel source
- **WHEN** the user confirms split-and-ingest from the novel summary page
- **THEN** the page SHALL call the shared splitter task API client method with the existing splitter request payload
- **AND** splitter task errors SHALL be surfaced through the shared API client error model

#### Scenario: Preserve split-and-ingest success behavior
- **WHEN** the splitter task request succeeds
- **THEN** the novel summary page SHALL keep the existing behavior of clearing the source file, refreshing project state, and clearing the split preview
