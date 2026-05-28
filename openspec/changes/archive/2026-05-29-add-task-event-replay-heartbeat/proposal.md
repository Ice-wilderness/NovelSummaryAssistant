## Why

Current task status summaries survive backend restart, but task event streams remain best-effort and do not support bounded replay, heartbeat detection, or `Last-Event-ID` recovery. Adding an explicit replay and heartbeat contract will make long-running task observation more reliable without introducing automatic restart-time recovery of running tasks.

## What Changes

- Persist a bounded per-task event log for task state, progress, log, warning, failure, and terminal events.
- Assign stable monotonically increasing event IDs and expose them through SSE so clients can reconnect with `Last-Event-ID`.
- Add SSE heartbeat events or comments so clients can distinguish an idle task stream from a broken connection.
- Replay eligible events after `Last-Event-ID`, then continue streaming live events.
- Preserve the existing restart behavior where non-terminal tasks loaded after backend restart become `interrupted`; automatic recovery of running tasks is explicitly out of scope.
- Add retention/cleanup rules for persisted task events to avoid unbounded local disk growth.
- Update the WebUI task subscription logic to track event IDs, reconnect safely, ignore duplicate events, process heartbeat messages, and keep the existing status-query fallback.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `task-runtime-api`: Add bounded task event persistence, event IDs, SSE heartbeat, and `Last-Event-ID` replay requirements while keeping restart-time non-terminal tasks as `interrupted`.
- `webui-workbench`: Add client-side task event replay/reconnect behavior and heartbeat-aware recovery requirements.

## Impact

- Backend task runtime event storage and cleanup under the existing runtime workspace.
- `/api/tasks/{task_id}/events` SSE response shape and reconnect behavior.
- Frontend task subscription hook and task status refresh behavior.
- Tests for event ID ordering, replay boundaries, heartbeat emission, cleanup, duplicate handling, and reconnect fallback.
