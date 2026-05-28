## 1. Backend Event Model And Storage

- [x] 1.1 Add additive `event_id` support to `TaskEvent` serialization/deserialization while preserving compatibility with old persisted summaries.
- [x] 1.2 Introduce a bounded per-task event-log store under the existing runtime workspace and keep lightweight task summaries compact.
- [x] 1.3 Persist emitted task events to the event log with monotonic per-task IDs and load retained logs for known persisted tasks.
- [x] 1.4 Implement retention and cleanup rules for stale or oversized event logs without blocking task execution on cleanup failure.

## 2. SSE Replay And Heartbeat

- [x] 2.1 Add runtime helpers for replaying retained events after a cursor and detecting replay gaps.
- [x] 2.2 Update `/api/tasks/{task_id}/events` to accept `Last-Event-ID` or an equivalent query cursor, replay retained events, then stream live events.
- [x] 2.3 Emit non-durable heartbeat frames while active task streams are idle.
- [x] 2.4 Preserve restart semantics: persisted non-terminal tasks still load as `interrupted` and are not automatically resumed.

## 3. WebUI Subscription Recovery

- [x] 3.1 Add `event_id` to frontend task event types and update the API client SSE subscription to support replay cursors and heartbeat frames.
- [x] 3.2 Update `useTaskActions` to track latest processed event IDs, ignore duplicate replayed events, reconnect with the latest cursor, and refresh task status on replay gaps or stream errors.
- [x] 3.3 Keep terminal handling unchanged from the user perspective: terminal or interrupted events refresh task status and close the active subscription.

## 4. Verification

- [x] 4.1 Add Python tests for event ID assignment, event-log persistence, replay order, replay gaps, retention cleanup, heartbeat streaming, and terminal/interrupted stream closure.
- [x] 4.2 Add frontend tests for cursor tracking, duplicate suppression, heartbeat handling, replay-gap fallback, and terminal refresh behavior.
- [x] 4.3 Run focused Python and frontend tests, then run `python -m pytest`, `npm run test`, `npm run build`, and `openspec validate --all`.

## 5. Documentation

- [x] 5.1 Update stability/backlog documentation to describe event replay and heartbeat as the planned recovery work while excluding automatic backend restart recovery of running tasks.
- [x] 5.2 Document the final event-log retention defaults and cleanup behavior after implementation.
