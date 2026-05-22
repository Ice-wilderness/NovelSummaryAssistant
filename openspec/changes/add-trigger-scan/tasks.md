## 1. Data Models And Defaults

- [x] 1.1 Add backend data models for trigger profiles, rule groups, trigger rules, scan config, ScanFinding, ScanEvent, ScanReport, and skip-list items.
- [x] 1.2 Add validation for matching policy, severity threshold, confidence range, scan mode, scan range, coarse batch size, and evidence quote length.
- [x] 1.3 Add built-in trigger template data for romance, character, violence, plot, and sensitive trigger groups.
- [x] 1.4 Add default trigger scan settings with safe fallback values.
- [x] 1.5 Add tests for model validation, default values, template initialization, and invalid configuration errors.
- [x] 1.6 Commit this feature block after the focused checks pass.

## 2. Trigger Profile Service

- [x] 2.1 Implement `workspace/trigger_profiles/` storage creation and path resolution.
- [x] 2.2 Implement trigger profile list, load, create, update, duplicate, and delete operations.
- [x] 2.3 Implement rule group create, rename, reorder, and guarded delete operations.
- [x] 2.4 Implement trigger rule create, update, enable/disable, reorder, and delete operations.
- [x] 2.5 Record profile version or snapshot metadata for scan compatibility checks.
- [x] 2.6 Add API endpoints for profile and rule management.
- [x] 2.7 Add backend tests for profile CRUD, group CRUD, rule validation, built-in template copies, deletion behavior, and version changes.
- [x] 2.8 Commit this feature block after the focused checks pass.

## 3. Chapter Granularity Refactor

- [x] 3.1 Update splitter request models and backend task start payloads to remove user-configurable `chapters_per_file`.
- [x] 3.2 Update `logic.chapter_splitter` and splitter strategies so output is always one chapter per file.
- [x] 3.3 Standardize generated chapter filenames to stable zero-padded chapter names where chapter order is known.
- [x] 3.4 Remove the chapter grouping control from `SplitterPage`.
- [x] 3.5 Add `summary_batch_size` to novel summary request models, defaults, frontend types, and `NovelSummaryPage`, with new-project default value 10.
- [x] 3.6 Update small-summary stage batching so `summary_batch_size` combines consecutive single-chapter files for one small-summary request.
- [x] 3.7 Keep `big_summary_batch_size` behavior unchanged for big summary batching.
- [x] 3.8 Add focused tests for single-chapter splitter output, request validation, summary batch grouping, and frontend type coverage.
- [x] 3.9 Commit this feature block after the focused checks pass.

## 4. Legacy Project Migration

- [x] 4.1 Implement legacy grouped chapter detection by filename range and by multiple chapter headings in one file.
- [x] 4.2 Add project status metadata for `requires_granularity_migration` and inferred legacy grouping size.
- [x] 4.3 Implement migration that first rewrites grouped chapter files into single-chapter files after user confirmation.
- [x] 4.4 Add a fallback flow that lets the user choose the original full novel TXT when direct grouped-file migration fails.
- [x] 4.5 Preserve original grouped files or a recoverable backup until migration succeeds.
- [x] 4.6 Store inferred legacy grouping size as project `summary_batch_size`.
- [x] 4.7 Expose migration check and migration execution APIs, including the original-TXT fallback path.
- [x] 4.8 Add WebUI prompts for migration-required projects before summary or trigger scan starts.
- [x] 4.9 Add tests for detection, successful direct migration, original-TXT fallback migration, failed migration metadata preservation, and imported project status recognition.
- [x] 4.10 Commit this feature block after the focused checks pass.

## 5. Small-Summary-Only Mode

- [x] 5.1 Add `stop_after_small_summary` to backend novel summary request models and task start handling.
- [x] 5.2 Refactor summarization orchestration so small-summary-only mode exits successfully after pending small summaries complete.
- [x] 5.3 Add API support for starting small-summary-only preparation from trigger scan prechecks.
- [x] 5.4 Add frontend action wiring for generating missing small summaries without running later summary stages.
- [x] 5.5 Add tests that small-summary-only mode does not run big, super, or ultimate summary stages.
- [x] 5.6 Commit this feature block after the focused checks pass.

## 6. Paragraph Indexing

- [x] 6.1 Create a paragraph indexing module for chapter title extraction, paragraph splitting, stable paragraph ids, and chunk metadata.
- [x] 6.2 Cache paragraph indexes under `.summarizer_cache/paragraph_index/` with invalidation based on file identity and content change.
- [x] 6.3 Provide context extraction for matched paragraphs with nearby paragraphs before and after the hit.
- [x] 6.4 Add tests for stable ids, cache reuse, cache invalidation, long chapter chunking, and context extraction.
- [x] 6.5 Commit this feature block after the focused checks pass.

## 7. Trigger Scan Core Pipeline

- [x] 7.1 Create the trigger scan module structure and shared JSON parsing helpers.
- [x] 7.2 Implement scan startup validation for project type, chapter files, selected profile, selected APIs, scan range, scan mode, `.md`/`.txt` summary coverage, migration requirement, and resumable state.
- [x] 7.3 Implement hybrid coarse scan over small-summary batches using `coarse_summary_batch_size` with default value 3.
- [x] 7.4 Implement precise scan over paragraph-indexed chapter text in configurable chapter batches using `precise_chapter_batch_size` with default value 5 and strict finding schema validation.
- [x] 7.5 Apply matching policy, severity threshold, minimum confidence, low-confidence retention, and skip-advice settings to raw findings.
- [x] 7.6 Implement optional verification with same-chapter finding batching, `verification_chapter_batch_size` default value 5, and independent verification API selection.
- [x] 7.7 Implement adjacent-paragraph finding merge and AI-assisted cross-chapter event aggregation.
- [x] 7.8 Persist chapter-level scan state to `.summarizer_cache/scan_state_{task_id}.json`.
- [x] 7.9 Implement resume logic that skips completed chapters when configuration, scan batch sizes, and profile version are compatible.
- [x] 7.10 Add tests for prechecks, `.md`/`.txt` summary discovery, coarse scan parsing, scan batch defaults, precise scan parsing, verification application, aggregation, thresholds, resume, cancel preservation, and invalid model output handling.
- [x] 7.11 Commit this feature block after the focused checks pass.

## 8. Reports, History, Skip Lists, And Export

- [x] 8.1 Implement ScanReport persistence under `<effective_project_output>/trigger_scan/`.
- [x] 8.2 Implement report history index creation, listing, loading, deletion, and imported-project detection.
- [x] 8.3 Implement partial report or recovery-state preservation for failed scans.
- [x] 8.4 Implement finding review updates for `confirmed`, `false_positive`, and user notes.
- [x] 8.5 Implement independent skip-list storage, add/remove/update operations, and chapter-grouped listing.
- [x] 8.6 Implement Markdown and JSON report export with advisory warning and evidence quote length enforcement.
- [x] 8.7 Implement Markdown skip-list export.
- [x] 8.8 Add tests for report persistence, history list, review actions, skip list behavior, exports, quote limits, and managed/custom output deletion behavior.
- [x] 8.9 Commit this feature block after the focused checks pass.

## 9. Prompt Workflow Integration

- [ ] 9.1 Add default prompt templates for `trigger_coarse_scan`, `trigger_precise_scan`, `trigger_verification`, and `trigger_aggregation`.
- [ ] 9.2 Add a trigger scanning workflow page to structured prompt configuration defaults.
- [ ] 9.3 Ensure prompt rendering supplies all trigger scan variables and rejects missing variables with clear errors.
- [ ] 9.4 Wire trigger scan stages to use saved workflow prompt nodes and reusable modules.
- [ ] 9.5 Add tests for prompt default loading, save/reset behavior, module expansion, and missing variable diagnostics.
- [ ] 9.6 Commit this feature block after the focused checks pass.

## 10. Task Runtime And Backend API

- [ ] 10.1 Add `trigger_scan` and small-summary-only task support to task type definitions, API payload models, and frontend types.
- [ ] 10.2 Implement `create_trigger_scan_runner` in workflow services.
- [ ] 10.3 Add trigger scan precheck, start, status, report, result action, skip list, export, context APIs, and scan batch configuration payload fields.
- [ ] 10.4 Emit structured scan progress events for stages, chapters, warnings, intermediate findings, and report completion.
- [ ] 10.5 Ensure task availability prevents concurrent summary or scan tasks.
- [ ] 10.6 Add API tests for validation errors, task creation, event streaming payloads, report APIs, context APIs, and concurrent task blocking.
- [ ] 10.7 Commit this feature block after the focused checks pass.

## 11. WebUI Trigger Scan Experience

- [ ] 11.1 Add `trigger_scan` view key, navigation item, icon, route selection, and page shell.
- [ ] 11.2 Build trigger profile management tab with profile list, create/edit/delete/duplicate, groups, rules, examples, negative examples, thresholds, and enable toggles.
- [ ] 11.3 Build scan configuration tab with project selector, range controls, mode selection, API selection, confidence controls, coarse/precise/verification batch size controls, advanced settings, and startup-check decision dialogs.
- [ ] 11.4 Wire small-summary generation, migration confirmation, range shrinking, mixed hybrid/precise choice, cancel, resume, and full rescan actions.
- [ ] 11.5 Build scan progress integration with existing LogPanel and task actions.
- [ ] 11.6 Build scan results tab with history selector, global spoiler slider, filters, event view, finding table, and loading/empty/error states.
- [ ] 11.7 Build context modal with highlighted paragraphs and missing-context warnings.
- [ ] 11.8 Build finding review actions, notes, per-item spoiler override, and add-to-skip-list actions.
- [ ] 11.9 Build skip-list view and MD/JSON export controls.
- [ ] 11.10 Add frontend tests or documented manual checks for tab navigation, configuration validation, scan batch controls, precheck decisions, live updates, filters, spoiler controls, context modal, review actions, and exports.
- [ ] 11.11 Commit this feature block after the focused checks pass.

## 12. Project Output And Import Integration

- [ ] 12.1 Update project output resolution so trigger scan artifacts use the selected project's effective output directory.
- [ ] 12.2 Update project deletion to remove managed trigger scan artifacts and preserve unmanaged custom output directories.
- [ ] 12.3 Update project import/status scanning to recognize trigger scan reports, skip lists, paragraph cache, `.md`/`.txt` summary outputs, and migration requirements.
- [ ] 12.4 Add tests for managed output cleanup, custom output preservation, imported trigger scan history, summary output format recognition, and migration status display.
- [ ] 12.5 Commit this feature block after the focused checks pass.

## 13. Summary Output Format

- [ ] 13.1 Add `summary_output_format` to backend novel summary request models, project metadata, frontend types, and default settings, accepting `md` and `txt` with new-project default `md`.
- [ ] 13.2 Update small, big, super, and ultimate summary writers to use the selected extension for user-visible outputs.
- [ ] 13.3 Update StateManager, summary readers, project progress/import scans, and trigger scan prechecks to discover both `.md` and `.txt` summary files.
- [ ] 13.4 Add a WebUI output format selector to `NovelSummaryPage` and persist/restore the project-level choice.
- [ ] 13.5 Add tests for default Markdown output, explicit TXT output, mixed-format resume/progress discovery, and trigger scan summary coverage discovery.
- [ ] 13.6 Commit this feature block after the focused checks pass.

## 14. End-To-End Verification

- [ ] 14.1 Run focused backend tests for profile, chapter granularity, migration, summary output format, small-summary-only, paragraph index, trigger scan pipeline, scan batch configuration, reports, exports, and API routes.
- [ ] 14.2 Run `pytest` for the full backend test suite and fix regressions.
- [ ] 14.3 Run `npm run typecheck` from `frontend/` and fix TypeScript errors.
- [ ] 14.4 Run the WebUI locally and manually verify a precise-mode scan on a small fixture project.
- [ ] 14.5 Manually verify hybrid mode prechecks for no summaries, partial summaries, and full summaries.
- [ ] 14.6 Manually verify legacy grouped project migration and `summary_batch_size` preservation.
- [ ] 14.7 Manually verify Markdown/TXT summary output, report history, spoiler switching, context viewing, review status updates, skip-list export, and Markdown/JSON report export.
- [ ] 14.8 Document any remaining known limitations before marking the change ready for implementation review.
- [ ] 14.9 Commit final verification documentation or cleanup changes after the checks pass.
