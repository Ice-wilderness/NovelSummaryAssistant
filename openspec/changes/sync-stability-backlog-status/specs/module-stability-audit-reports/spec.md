## ADDED Requirements

### Requirement: Follow-up status reflects completed changes
The audit follow-up documentation SHALL distinguish historical findings from current unresolved work by incorporating relevant archived OpenSpec changes and current module layout before presenting next-step priorities.

#### Scenario: Completed work is not listed as unresolved
- **WHEN** an OpenSpec change has been archived and the current repository layout shows the work is complete
- **THEN** the audit overview or follow-up backlog SHALL list that work as completed or remove it from unresolved priority lists

#### Scenario: Historical findings remain traceable
- **WHEN** an original module report still describes a risk that has since been mitigated
- **THEN** the current-state overview or backlog SHALL clarify the newer status without requiring the original historical finding text to be rewritten

### Requirement: Documentation structure reflects current module boundaries
The project-facing documentation SHALL describe major backend and frontend module boundaries using the current repository structure when those boundaries are relevant to maintainer planning.

#### Scenario: README module list is current
- **WHEN** maintainers read the README project structure section
- **THEN** it SHALL show current backend route and workspace service module boundaries rather than only the older concentrated file responsibilities
