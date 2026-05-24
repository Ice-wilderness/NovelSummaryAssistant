## 1. Baseline And Compatibility

- [x] 1.1 Review current task/runtime, trigger scan, project output, and prompt editor tests to identify the narrowest existing tests to extend.
- [x] 1.2 Add or update fixtures for cancelled business runners, resumed trigger scans with historical findings, partial trigger scan reports, and managed/custom output directories.
- [x] 1.3 Add compatibility assertions for old trigger scan reports and old project metadata that do not yet contain `partial_failed`, warnings, verification metadata, or output ownership metadata.

## 2. Unified Task Cancellation And Event Recovery

- [x] 2.1 Update novel summary, article summary, custom summary, chapter splitting, and trigger scan runners so user cancellation propagates as `asyncio.CancelledError` to `TaskRuntime`.
- [x] 2.2 Update `TaskRuntime` terminal handling so accepted user cancellation is recorded and emitted as `cancelled`, not `failed` or successful completion.
- [x] 2.3 Ensure task event streams emit or expose terminal completion so clients do not wait indefinitely after `completed`, `failed`, `cancelled`, or `partial_failed`.
- [x] 2.4 Add runner-level cancellation tests for novel summary, article summary, custom summary, chapter splitting, and trigger scan.
- [x] 2.5 Update frontend task subscription handling to fetch latest task status after SSE error/disconnect and preserve backend terminal states.

## 3. Trigger Scan Pause, Resume, Verification, And Status

- [x] 3.1 Replace non-blocking `pause_signal.wait(0)` usage in precise scan and verification paths with an async pause gate that blocks before starting additional API calls.
- [x] 3.2 Refactor trigger scan progress accounting to track `selected_total`, `completed_from_resume`, `pending_total`, and `processed_current_run` without overwriting cumulative completed counts.
- [x] 3.3 Update scan state/report models to preserve finding verification state and enough provenance to distinguish new findings from historical findings.
- [x] 3.4 Implement resume verification policy: verify new findings, reverify historical findings with missing/unknown verification state when context can be rebuilt, and mark unrecoverable findings with `unverified` warnings.
- [x] 3.5 Implement report status rules so full selected-range success becomes `completed`, non-cancel partial execution becomes `partial_failed`, and user cancellation never produces a `completed` report.
- [x] 3.6 Add targeted tests for real pause blocking, resumed progress denominator, historical finding verification, `unverified` warnings, and `partial_failed` status.

## 4. Prompt Aggregation Contract

- [ ] 4.1 Keep runtime trigger scan aggregation deterministic and ensure no LLM aggregation call is introduced in this change.
- [ ] 4.2 Update prompt workflow metadata/API so aggregation is not presented as an active LLM prompt node, or is clearly labeled as not affecting current scan results.
- [ ] 4.3 Update the prompt editor UI to show precise scan and verification as active trigger scan prompt nodes and to avoid implying aggregation prompt edits affect runtime.
- [ ] 4.4 Record the deferred B plan for future LLM aggregation, including API cost, JSON parsing, fallback behavior, and UI disclosure topics.
- [ ] 4.5 Add tests or assertions that saving precise/verification prompts affects later runs, while aggregation prompt content is not required for deterministic aggregation.

## 5. Output Directory Ownership And Diagnostics

- [ ] 5.1 Add ownership metadata for backend-created managed export directories, including project slug and managed directory purpose.
- [ ] 5.2 Update project deletion to remove output directories only when ownership metadata matches the project being deleted.
- [ ] 5.3 Preserve custom, imported, missing-metadata, or ownership-mismatched output directories and return enough information for the WebUI to explain that files were kept.
- [ ] 5.4 Preserve complete non-secret API failure diagnostic input/output content while continuing to redact API keys, authorization headers, and similar credentials.
- [ ] 5.5 Add an API failure-log cleanup or retention path that removes old diagnostic files without truncating newly written failure diagnostics by default.
- [ ] 5.6 Add project workspace and diagnostic logging tests for ownership deletion, preserved custom directories, full diagnostic content, secret redaction, and cleanup behavior.

## 6. Frontend Status And Warning Surfaces

- [ ] 6.1 Update task and report status labels to display `cancelled`, `partial_failed`, and preserved partial results distinctly from generic failure.
- [ ] 6.2 Show trigger scan report warnings for unverified findings, missing context, and preserved partial results near the report summary or affected result area.
- [ ] 6.3 Refresh project history and selected project status after terminal events and after SSE fallback task status fetches.
- [ ] 6.4 Add focused frontend tests or equivalent build-time assertions for task status recovery, partial scan display, unverified warning display, and prompt aggregation labeling.

## 7. Git Checkpoints

- [ ] 7.1 After each independently verifiable subfeature or task subset is completed, run the narrowest relevant verification before starting the next subfeature.
- [ ] 7.2 Commit each completed subfeature to git with a focused commit containing only related code, tests, and documentation changes.
- [ ] 7.3 Before each commit, review `git status` and the diff to avoid staging unrelated user changes or unfinished follow-up work.

## 8. Verification

- [ ] 8.1 Run targeted Python tests for task runtime, workflow services, trigger scan pipeline/reporting, project workspace, and LLM diagnostics.
- [ ] 8.2 Run the full backend test suite with `python -m pytest`.
- [ ] 8.3 Run frontend validation with `npm run build`.
- [ ] 8.4 Manually review the generated OpenSpec deltas against the implemented behavior before archive.
