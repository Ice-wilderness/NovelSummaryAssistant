# chapter-processing-granularity Specification

## Purpose
TBD - created by archiving change add-trigger-scan. Update Purpose after archive.
## Requirements
### Requirement: Single-Chapter Split Output
The system SHALL split novel source text into one output text file per chapter.

#### Scenario: Split source into single-chapter files
- **WHEN** the user starts a chapter split task with a valid source text
- **THEN** the backend SHALL write each detected chapter to its own `.txt` file
- **AND** the backend SHALL NOT combine multiple chapters into one output file

#### Scenario: Name chapter files consistently
- **WHEN** the splitter can determine chapter order
- **THEN** the backend SHALL name generated chapter files with stable zero-padded chapter numbering such as `第001章.txt`
- **AND** the file contents SHALL preserve the chapter title when available

#### Scenario: Remove chapter grouping control
- **WHEN** the user opens the chapter splitting page
- **THEN** the WebUI SHALL NOT show a `chapters_per_file` or equivalent split grouping control

### Requirement: Summary Batch Size
The system SHALL decouple summary input batching from chapter split file boundaries.

#### Scenario: Default summary batch size
- **WHEN** the user creates a new novel summary project or opens novel summary settings without a saved value
- **THEN** the WebUI SHALL default `summary_batch_size` to 10
- **AND** the backend SHALL use 10 when a request omits `summary_batch_size`

#### Scenario: Configure small summary batch size
- **WHEN** the user opens the novel summary page
- **THEN** the WebUI SHALL provide a positive integer `summary_batch_size` control for the number of single-chapter files combined into one small-summary request

#### Scenario: Summarize batches of single chapters
- **WHEN** a novel summary task starts with `summary_batch_size` greater than 1
- **THEN** the backend SHALL combine that many consecutive single-chapter files for each small-summary API call
- **AND** the backend SHALL keep the original chapter files unchanged

#### Scenario: Summarize one chapter per request
- **WHEN** a novel summary task starts with `summary_batch_size` equal to 1
- **THEN** the backend SHALL send one chapter file per small-summary API call

### Requirement: Summary Output Format
The system SHALL allow novel summary outputs to use Markdown or plain text while preserving downstream discovery.

#### Scenario: Default summary output format
- **WHEN** the user creates a new novel summary project or opens novel summary settings without a saved value
- **THEN** the WebUI SHALL default `summary_output_format` to `md`
- **AND** the backend SHALL use `md` when a request omits `summary_output_format`

#### Scenario: Configure summary output format
- **WHEN** the user opens the novel summary page
- **THEN** the WebUI SHALL provide a `summary_output_format` choice with `md` and `txt`
- **AND** the backend SHALL reject any other value with an actionable validation error

#### Scenario: Write selected summary format
- **WHEN** small, big, super, or ultimate summary outputs are written
- **THEN** the backend SHALL use the selected `.md` or `.txt` extension for user-visible summary files
- **AND** the backend SHALL preserve the selected format in project settings for later resume or reload

#### Scenario: Discover existing summary formats
- **WHEN** the backend reads existing summaries for later summary stages, project progress, project import, or trigger scan prechecks
- **THEN** the backend SHALL discover both `.md` and `.txt` summary files
- **AND** valid `.md` summary files SHALL NOT be treated as missing because older code expected `.txt`

### Requirement: Legacy Multi-Chapter Project Detection
The system SHALL detect projects whose chapter files use legacy multi-chapter grouping.

#### Scenario: Detect grouped chapter filename
- **WHEN** a project contains chapter files with names indicating a range such as `第1章-第20章.txt`
- **THEN** the backend SHALL mark the project as requiring granularity migration before trigger scanning

#### Scenario: Detect grouped chapter content
- **WHEN** a project file contains multiple chapter headings even if its filename does not expose a range
- **THEN** the backend SHALL mark the project as requiring granularity migration before trigger scanning

#### Scenario: Report migration requirement
- **WHEN** the WebUI loads a project that requires granularity migration
- **THEN** the WebUI SHALL explain that single-chapter files are required for precise paragraph-level scanning
- **AND** the WebUI SHALL NOT silently start trigger scanning against grouped files

### Requirement: Legacy Multi-Chapter Project Migration
The system SHALL migrate legacy grouped chapter projects into single-chapter files after user confirmation.

#### Scenario: Confirm and migrate legacy project
- **WHEN** the user confirms migration for a detected legacy project
- **THEN** the backend SHALL split grouped chapter files into single-chapter files
- **AND** the backend SHALL update project metadata to indicate the project uses single-chapter granularity

#### Scenario: Preserve previous summary grouping intent
- **WHEN** migration can infer the old grouped chapter count
- **THEN** the backend SHALL store that value as the project's `summary_batch_size`

#### Scenario: Migration failure preserves metadata
- **WHEN** legacy project migration fails
- **THEN** the backend SHALL return an actionable error
- **AND** the backend SHALL NOT mark the project as migrated
- **AND** the backend SHALL NOT discard the original grouped files

#### Scenario: Fallback to original source text
- **WHEN** direct migration from grouped chapter files fails
- **THEN** the WebUI SHALL allow the user to choose the original full novel TXT
- **AND** the backend SHALL use that source text to regenerate single-chapter files for the project after confirmation

### Requirement: Small-Summary-Only Execution
The system SHALL support generating only small summaries without advancing to later summary stages.

#### Scenario: Stop after small summary
- **WHEN** a task starts with the small-summary-only option
- **THEN** the backend SHALL execute pending small-summary work
- **AND** the backend SHALL stop before big summary, super summary, and ultimate summary stages

#### Scenario: Use for trigger scan preparation
- **WHEN** hybrid trigger scanning requires missing small summaries
- **THEN** the WebUI SHALL offer an action that starts a small-summary-only task for the affected project

