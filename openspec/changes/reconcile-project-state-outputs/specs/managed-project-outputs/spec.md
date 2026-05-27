## ADDED Requirements

### Requirement: Project State Output Reconciliation

The system SHALL reconcile managed project state records, persisted task summaries, intermediate artifacts, and expected output files before presenting a historical or imported project's current status.

#### Scenario: Reconcile project on history load
- **WHEN** the backend lists managed project history
- **THEN** each returned project summary SHALL include a reconciliation status derived from the latest readable project metadata, persisted task summary, intermediate artifacts, and expected output files
- **AND** unreadable or missing optional reconciliation inputs SHALL be reported as project warnings instead of preventing the history list from loading

#### Scenario: Reconcile project on detail load
- **WHEN** the WebUI loads details for a historical project
- **THEN** the backend SHALL return the project's reconciliation status, reconciliation warnings, expected output checks, and any available repair plan together with the restorable project details

#### Scenario: Reconcile imported project
- **WHEN** an existing project directory is imported
- **THEN** the backend SHALL run the same reconciliation checks used for historical project detail loading before returning the imported project's recognized status

#### Scenario: Completed state with available outputs
- **WHEN** project state or a persisted task summary records a completed or partial result and all required output files for that result are present and readable
- **THEN** the reconciliation status SHALL be `ok`
- **AND** the project SHALL preserve the recorded task terminal state

#### Scenario: Completed state with missing required output
- **WHEN** project state or a persisted task summary records a completed or partial result but one or more required output files are missing, unreadable, or inconsistent with the saved output format
- **THEN** the reconciliation status SHALL be `abnormal_completed`
- **AND** the response SHALL include warnings that identify the missing or inconsistent outputs
- **AND** the response SHALL preserve the recorded task terminal state instead of remapping it to incomplete or failed

#### Scenario: Output exists without reliable completed state
- **WHEN** expected generated outputs exist but project state and persisted task summaries do not contain a reliable completed or partial terminal state
- **THEN** the reconciliation status SHALL include a warning that state metadata is incomplete
- **AND** the backend SHALL NOT silently mark the project as normally completed without recording that warning

#### Scenario: Project has no completed state and no generated output
- **WHEN** project state has no reliable completed or partial terminal state and expected generated outputs are absent
- **THEN** the reconciliation status SHALL be incomplete rather than `abnormal_completed`

### Requirement: Project Output Repair Plan

The system SHALL produce a repair plan for reconciled projects when missing or inconsistent outputs can potentially be restored from available inputs, intermediate artifacts, or a user-confirmed rerun.

#### Scenario: Generate repair plan for abnormal completed project
- **WHEN** reconciliation classifies a project as `abnormal_completed`
- **THEN** the backend SHALL return a repair plan containing available repair actions, blocked actions, required inputs, output effects, whether an action may call an LLM API, and whether an action may overwrite existing files

#### Scenario: Repair from intermediate artifacts
- **WHEN** only a final output file is missing and the intermediate artifacts needed to rebuild it are present and readable
- **THEN** the repair plan SHALL include an action that rebuilds the final output from those intermediate artifacts
- **AND** the action SHALL disclose whether it requires a new LLM API call

#### Scenario: Repair by rerunning missing stages
- **WHEN** one or more intermediate artifacts are missing but source files, chapter files, saved settings, and required API configuration are available
- **THEN** the repair plan SHALL include an action to rerun only the missing stages that can be safely identified
- **AND** the action SHALL disclose that outputs may differ from the original run when LLM calls are required

#### Scenario: Block unsafe repair
- **WHEN** required source files, chapter files, saved settings, or API configuration needed for a repair action are missing or unreadable
- **THEN** the repair plan SHALL mark that action as blocked with a user-readable reason
- **AND** the backend SHALL NOT fabricate missing inputs or silently fall back to a broader rerun

#### Scenario: Preserve existing outputs by default
- **WHEN** a repair action would write a path that already contains a generated output file
- **THEN** the repair plan SHALL mark the action as requiring overwrite confirmation or SHALL choose a non-conflicting output path
- **AND** the system SHALL NOT overwrite existing output files as part of reconciliation alone

#### Scenario: No silent repair
- **WHEN** reconciliation detects missing or inconsistent outputs
- **THEN** the backend SHALL NOT rebuild files, rerun workflow stages, or call an LLM API until the user explicitly starts a repair action
