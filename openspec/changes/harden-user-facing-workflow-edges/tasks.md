## 1. Legacy Trigger Scan Report Compatibility

- [x] 1.1 Inspect current trigger scan report load/list/detail mapping and add narrow detection for legacy `failed` reports that still contain readable findings or events.
- [x] 1.2 Expose additive compatibility metadata or warnings through the report API without rewriting old report files or changing modern `partial_failed` reports.
- [x] 1.3 Update trigger scan report history/detail display labels so legacy-compatible reports are shown as historical partial failures, not completed successes.
- [x] 1.4 Add backend reporting tests and frontend report display tests covering legacy-compatible, modern `partial_failed`, and normal `completed` reports.

## 2. API Attempts And Parse Retry Semantics

- [x] 2.1 Update API configuration labels, hints, and tests so `max_retries` is presented as API total attempts including the first request.
- [x] 2.2 Introduce an independent trigger scan parse retry concept such as `parse_retries` or equivalent internal naming without changing saved API configuration semantics.
- [x] 2.3 Update trigger scan parse failure handling, logs, diagnostics, and final errors so exhausted API attempts and exhausted parse retries are distinguishable.
- [x] 2.4 Add focused backend tests for API total-attempt boundaries, parse retry exhaustion, and combined failure messaging.

## 3. Task Event Subscription Cache Cleanup

- [x] 3.1 Update `useTaskActions` terminal handling to clear a task's replay cursor and processed event id set only after terminal status refresh and subscription closure.
- [x] 3.2 Ensure active non-terminal reconnect behavior still preserves replay cursor and duplicate-event suppression state.
- [x] 3.3 Add focused `useTaskActions` tests for terminal cleanup, active reconnect preservation, and isolation from other active tasks.

## 4. Frontend Core Flow Regression Baseline

- [x] 4.1 Add or extend novel summary page tests for terminal status text, warning/error visibility, disabled invalid actions, and project status refresh.
- [x] 4.2 Add or extend article summary and custom summary tests for `partial_failed`, failure, cancellation, and available output/warning display.
- [x] 4.3 Add or extend splitter flow tests for running-state disabled actions, terminal state display, API errors, and project refresh after terminal outcomes.
- [x] 4.4 Add or extend trigger scan results tests for completed, modern partial-failed, legacy-compatible, and warning-bearing report views.

## 5. Verification

- [x] 5.1 Run focused Python tests for trigger scan reporting and retry semantics.
- [x] 5.2 Run focused frontend tests for API config, `useTaskActions`, summary pages, splitter flow, and trigger scan results.
- [x] 5.3 Run the relevant broader checks: `python -m pytest`, frontend test/build commands, and `openspec validate --all` when the implementation is complete.
