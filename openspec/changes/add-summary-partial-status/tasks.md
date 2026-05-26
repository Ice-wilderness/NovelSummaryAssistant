## 1. Runtime Outcome Model

- [x] 1.1 Add backend support for `partial_failed` as a terminal `TaskStatus` and ensure terminal checks treat it as finished.
- [x] 1.2 Add a backward-compatible structured task outcome type with status, result summary, error, warnings, and optional data.
- [x] 1.3 Update `TaskRuntime` to normalize old string runner results and new structured outcomes without changing existing runner behavior.
- [x] 1.4 Extend task record serialization and frontend API types with warnings/result data defaults that remain compatible with old records.
- [x] 1.5 Add focused task runtime tests for string runner compatibility, structured `partial_failed`, terminal events, and warnings/result data serialization.

## 2. Article Summary Partial Status

- [ ] 2.1 Update article summary logic to record failed section files with stage and error summary when section-level generation fails.
- [ ] 2.2 Return a partial article result when at least one section failed, at least one section summary is available, and final summary generation succeeds.
- [ ] 2.3 Return failed status when no section summary is available or final summary generation fails without a new usable final result.
- [ ] 2.4 Persist article partial metadata in the existing article state file or a colocated status file so project reloads can surface warnings.
- [ ] 2.5 Add focused article summary tests for full success, partial section failure with final output, all sections failed, and final generation failure.

## 3. Custom Summary Partial Status

- [ ] 3.1 Update custom summary logic to record source files that fail during material reading.
- [ ] 3.2 Return a partial custom summary result when at least one material file fails, at least one material file is read, and the final LLM output succeeds.
- [ ] 3.3 Return failed status when all selected materials fail to read or the final LLM call fails without generated output.
- [ ] 3.4 Update the custom summary workflow runner to map custom summary result objects into structured task outcomes.
- [ ] 3.5 Add focused custom summary tests for full success, partial material failure with output, all materials failed, and API failure.

## 4. Workflow Services And Project State

- [ ] 4.1 Update article summary workflow runner to map article summary result objects into structured task outcomes.
- [ ] 4.2 Ensure project history/latest task status preserves `partial_failed` for article summary and custom summary tasks.
- [ ] 4.3 Ensure summary partial warnings and failed-unit details are available through task status responses without parsing logs.
- [ ] 4.4 Add workflow service/API tests for article and custom summary `partial_failed` task responses and project history display data.

## 5. WebUI Display

- [ ] 5.1 Update shared task status display helpers to label summary `partial_failed` as a partial result rather than generic failure.
- [ ] 5.2 Update the article summary page to show partial warnings, failed sections, and the retained final output/result location.
- [ ] 5.3 Update the custom summary page to show partial warnings, failed source files, and retained generated output.
- [ ] 5.4 Add focused Vitest tests for article/custom partial status labels, warning display, missing-warning fallback, and retained result display.

## 6. Verification And Git Checkpoints

- [ ] 6.1 Run the narrowest Python tests after each backend block, starting with task runtime and summary logic tests.
- [ ] 6.2 Run the narrowest frontend tests after WebUI changes.
- [ ] 6.3 Run `python -m pytest`, `npm run test`, `npm run build`, and `openspec validate --all` before marking the change complete.
- [ ] 6.4 Create focused Conventional Commits checkpoints after each independently verified implementation block.
