## ADDED Requirements

### Requirement: Legacy Report Compatibility Status
系统 SHALL distinguish legacy trigger scan reports that contain preserved findings from fully completed reports when loading report history and report details.

#### Scenario: Load legacy failed report with findings
- **WHEN** the backend reads a saved trigger scan report with legacy status `failed`, preserved findings or events, and no modern `partial_failed` status metadata
- **THEN** the report response SHALL keep the available findings or events readable
- **AND** the response SHALL include compatibility metadata or a warning identifying the report as a historical partial-failure/legacy-compatible report
- **AND** the response SHALL NOT present that report as an ordinary `completed` success

#### Scenario: Display legacy compatibility report
- **WHEN** the WebUI displays a legacy-compatible trigger scan report in report history or report details
- **THEN** the WebUI SHALL show a readable legacy partial-failure label such as "历史部分失败" or equivalent wording
- **AND** the WebUI SHALL keep available findings, events, and warnings accessible
- **AND** the WebUI SHALL show the compatibility warning near the report summary or status area

#### Scenario: Preserve modern partial failure display
- **WHEN** the WebUI displays a trigger scan report whose status is already `partial_failed`
- **THEN** the WebUI SHALL use the normal partial-failure display and warnings
- **AND** the WebUI SHALL NOT label the report as legacy-compatible solely because findings are present
