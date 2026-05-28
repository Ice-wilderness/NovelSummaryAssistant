## Context

`TaskRuntime` currently keeps live events in each in-memory `TaskRecord.events` list and an `asyncio.Queue`, while lightweight task summaries are persisted under `workspace/task_summaries/`. Persisted summaries intentionally keep only a terminal or interrupted summary event, so `/api/tasks/{task_id}` remains useful after restart but `/api/tasks/{task_id}/events` cannot replay historical progress or recover from a missed SSE window.

The WebUI already refreshes task status after an SSE error and terminal event, but it does not track event IDs or reconnect from the last processed event. This change strengthens observation and recovery only; it does not try to restart backend work that was interrupted by process exit.

## Goals / Non-Goals

**Goals:**

- Give every task event a stable, monotonic event ID that is preserved in API responses and SSE frames.
- Persist a bounded per-task event log separate from lightweight task summaries.
- Let clients replay retained events after `Last-Event-ID` before receiving live events.
- Emit heartbeat frames during idle streams so the client can tell the stream is still alive.
- Keep persisted event logs bounded by local retention limits and cleanup.
- Update WebUI subscriptions to track event IDs, reconnect safely, ignore duplicates, and keep status-query fallback behavior.

**Non-Goals:**

- Do not automatically resume `pending`, `running`, `paused`, or `canceling` tasks after backend restart.
- Do not guarantee full historical event replay beyond configured retention limits.
- Do not add a remote/multi-user task event storage service.
- Do not change existing task start, pause, resume, cancel, or persisted summary APIs except for adding event IDs and replay behavior.

## Decisions

1. Store event history separately from summary JSON.

   The lightweight task summary should stay compact and optimized for status queries. A new event-log store under the existing runtime workspace can persist full retained events without making `/api/tasks` responses grow with every log line.

2. Use per-task monotonically increasing integer event IDs.

   Integer IDs are easy to compare, serialize, and test. They avoid timestamp ordering edge cases and let the backend replay events with `event_id > Last-Event-ID` in original order. Existing event consumers can treat `event_id` as additive metadata.

3. Support both SSE `Last-Event-ID` and a query replay cursor.

   Browsers may send `Last-Event-ID` automatically during native EventSource reconnects, but application-level reconnects cannot set custom headers. Accepting an equivalent `last_event_id` query parameter keeps the WebUI implementation straightforward while preserving standard SSE semantics.

4. Make heartbeat frames non-durable.

   Heartbeats prove connection liveness but are not task history. They should not advance the durable task event cursor and should not appear in task records or replay logs.

5. Treat replay gaps as recoverable observation gaps.

   If the requested cursor is older than retained history or invalid, the stream should not fail just because replay is incomplete. The backend should surface a current state event or replay-gap marker, then continue live streaming or close for inactive tasks; the WebUI should also refresh `/api/tasks/{task_id}`.

6. Keep restart semantics explicit.

   Existing persisted summaries already convert non-terminal tasks loaded after restart to `interrupted`. This change preserves that rule. Event replay improves visibility into retained history, not execution recovery.

## Risks / Trade-offs

- Event logs can grow on long, chatty tasks -> Bound by retention limits and prune old events per task.
- A replay gap can still miss detailed logs -> Emit a replay-gap signal and refresh the task status so the visible lifecycle state remains correct.
- Native EventSource reconnect behavior varies by browser -> Track the last processed event in application state and support query-based reconnect cursors.
- Duplicate replay/live overlap can append repeated log lines -> Deduplicate by task ID and event ID in the WebUI before appending.
- Event IDs add compatibility surface -> Keep the field additive and preserve existing event payload fields.

## Migration Plan

- Existing persisted task summaries without event IDs remain readable.
- Loaded terminal or interrupted tasks without retained event logs continue to expose a terminal/interrupted state event.
- New task events receive IDs and are written to the bounded event log.
- WebUI code accepts both old events without `event_id` and new replayable events with `event_id` during the transition.

## Open Questions

- Exact default retention values should be chosen during implementation based on current task log volume and local disk expectations.
