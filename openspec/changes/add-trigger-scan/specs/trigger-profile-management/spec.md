## ADDED Requirements

### Requirement: Trigger Profile Storage
The system SHALL store trigger profiles globally outside individual project output directories.

#### Scenario: Create profile storage
- **WHEN** the backend starts and `workspace/trigger_profiles/` does not exist
- **THEN** the backend SHALL create the profile storage directory when trigger profile data is first needed

#### Scenario: Persist trigger profile
- **WHEN** the user creates or edits a trigger profile
- **THEN** the backend SHALL persist the profile with stable `id`, `name`, `description`, timestamps, rule groups, and rules

#### Scenario: Load profile list
- **WHEN** the WebUI requests trigger profiles
- **THEN** the backend SHALL return all saved profiles sorted by recent update time or stable display order

### Requirement: Trigger Profile CRUD
The system SHALL allow users to create, rename, edit, duplicate, and delete trigger profiles.

#### Scenario: Create trigger profile
- **WHEN** the user submits a valid profile name
- **THEN** the backend SHALL create a new trigger profile with an empty or template-derived rule set

#### Scenario: Update trigger profile metadata
- **WHEN** the user changes a profile name or description
- **THEN** the backend SHALL save the updated metadata and refresh `updated_at`

#### Scenario: Delete trigger profile
- **WHEN** the user deletes a trigger profile
- **THEN** the backend SHALL remove that profile from the global profile store
- **AND** existing scan reports that contain profile snapshots SHALL remain readable

### Requirement: Rule Group Management
The system SHALL allow users to organize trigger rules into editable display groups.

#### Scenario: Create rule group
- **WHEN** the user adds a rule group to a profile
- **THEN** the backend SHALL assign a stable group id and persist the group's name and rule ordering

#### Scenario: Rename rule group
- **WHEN** the user renames a rule group
- **THEN** rules in that group SHALL keep their group association

#### Scenario: Delete rule group
- **WHEN** the user deletes a rule group
- **THEN** the WebUI SHALL require the user to move or delete contained rules before the deletion is completed

### Requirement: Trigger Rule Configuration
The system SHALL allow each trigger rule to define matching behavior and examples.

#### Scenario: Save trigger rule
- **WHEN** the user saves a trigger rule
- **THEN** the backend SHALL persist `id`, `name`, `group_id`, `description`, `matching_policy`, `severity_threshold`, `enabled`, `examples`, and `negative_examples`

#### Scenario: Validate matching policy
- **WHEN** a trigger rule is saved
- **THEN** the backend SHALL accept only `explicit_only`, `explicit_or_strongly_implied`, or `any_hint` as `matching_policy`

#### Scenario: Validate severity threshold
- **WHEN** a trigger rule is saved
- **THEN** the backend SHALL require `severity_threshold` to be an integer from 1 through 5

### Requirement: Built-In Trigger Templates
The system SHALL provide editable built-in trigger rule templates grouped by trigger category.

#### Scenario: Initialize built-in templates
- **WHEN** no trigger profiles exist
- **THEN** the backend SHALL provide a default profile containing built-in groups for romance, character, violence, plot, and sensitive triggers

#### Scenario: Edit built-in template copy
- **WHEN** the user edits a built-in rule in a saved profile
- **THEN** the backend SHALL save the edit to that user's profile copy
- **AND** the backend SHALL NOT require the original template to remain immutable in the UI

### Requirement: Rule Version Tracking
The system SHALL track rule changes enough to warn about potentially stale scan results.

#### Scenario: Record rule version on scan
- **WHEN** a scan starts with a trigger profile
- **THEN** the backend SHALL record a profile snapshot or version marker with the scan configuration

#### Scenario: Warn after rule changes
- **WHEN** the user resumes or reruns a scan after the selected profile's rules changed
- **THEN** the WebUI SHALL warn that previous results may not match the current rules
- **AND** the WebUI SHALL offer a full rescan action
