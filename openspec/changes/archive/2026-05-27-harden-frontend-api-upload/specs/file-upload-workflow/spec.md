## ADDED Requirements

### Requirement: Client Upload Size Preflight
The WebUI SHALL reject text files that exceed the backend single-file upload size limit before reading their contents into browser memory.

#### Scenario: Reject oversized managed project upload
- **WHEN** the user selects a file larger than 100 MB in a managed workflow upload control
- **THEN** the WebUI SHALL reject the file before calling `arrayBuffer()`
- **AND** the WebUI SHALL display an actionable upload-size error
- **AND** the WebUI SHALL NOT submit that file to the backend upload API

#### Scenario: Reject oversized novel source split upload
- **WHEN** the user selects a novel source file larger than 100 MB for split preview or split-and-ingest
- **THEN** the WebUI SHALL reject the file before reading it into memory
- **AND** the WebUI SHALL display an actionable upload-size error
- **AND** the WebUI SHALL NOT retain that source file for preview or splitting

#### Scenario: Accept file within upload limit
- **WHEN** the user selects a text file whose size is less than or equal to 100 MB
- **THEN** the WebUI SHALL continue using the existing text decoding and upload or preview workflow
