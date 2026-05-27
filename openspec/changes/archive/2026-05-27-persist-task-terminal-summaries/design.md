## Context

`TaskRuntime` currently stores task handles in an in-memory dictionary. `/api/tasks/{task_id}` and `/api/tasks/{task_id}/events` can only observe records that still exist in the current backend process. Managed project metadata stores `latest_task_id` and `latest_task_status`, but after a backend restart the runtime cannot resolve that task id, and project pages fall back to filesystem progress heuristics.

This change focuses on making task status durable enough for user-facing recovery after restart. It does not attempt to resume Python coroutines or replay the full SSE event stream.

## Goals / Non-Goals

**Goals:**

- Persist a lightweight task summary whenever a task is created, changes important lifecycle state, or reaches a terminal state.
- Load persisted summaries when the backend starts so `/api/tasks/{task_id}` and `/api/tasks` can return recent known tasks.
- Mark persisted non-terminal tasks as `interrupted` during startup, with a clear warning/error explaining that the backend restarted before the task finished.
- Keep project history aligned with loaded persisted task summaries when a project references `latest_task_id`.
- Preserve existing terminal states and `partial_failed` result details.

**Non-Goals:**

- No automatic recovery of running background work after backend restart.
- No full task event log persistence or `Last-Event-ID` replay.
- No SSE heartbeat protocol in this change.
- No change to workflow-level resume logic based on existing cache/state files.

## Decisions

### Persist summaries in a runtime task-summary store

Add an optional storage directory to `TaskRuntime`, passed from `create_app` using the runtime base path, for example `<runtime_base>/workspace/task_summaries/`. The runtime writes one JSON file per task id.

Alternative considered: store task summaries only inside each project metadata file. That would make `/api/tasks/{task_id}` expensive or incomplete because not every task is project-scoped, and lookup would require scanning projects.

### Store lightweight task records, not full event history

Persist the serializable task record fields needed by status surfaces: ids, type, lifecycle status, progress text, timestamps, result summary, error, warnings, result data, params summary, and a minimal terminal/interruption event. Do not persist the full in-memory `events` list as a replay log.

Alternative considered: append every event to disk. That is closer to full SSE replay but introduces log growth, ordering, and `Last-Event-ID` semantics that belong in a later event-replay change.

### Introduce `interrupted` as an inactive task state

When `TaskRuntime` loads a persisted record whose status is `pending`, `running`, `paused`, or `canceling`, it converts the loaded summary to `interrupted`. The record gets an actionable error/warning such as “后端重启时任务仍未结束，无法自动恢复，请重新启动或从项目进度继续。”

Alternative considered: map these records to `failed`. That is misleading because the workflow may have been stopped by process restart rather than a business failure. `interrupted` keeps the distinction visible.

### Keep terminal SSE behavior minimal after restart

For a persisted terminal or interrupted record, `/api/tasks/{task_id}/events` may emit a synthetic final state event and close. It does not replay historical logs. Live tasks continue using the in-memory queue.

Alternative considered: return 404 for event streams after restart. That would preserve the current behavior but leaves the frontend without a clean way to close stale subscriptions once task status is recoverable.

### Preserve compatibility with old metadata

If a project references a `latest_task_id` that has no persisted summary, existing project progress recognition remains the fallback. Missing summary files must not make project loading fail.

Alternative considered: require all historical projects to have task summary files. That would break existing local workspaces created before this change.

## Risks / Trade-offs

- Persisted summaries can become stale or corrupted → load failures should skip the bad summary, log or surface a warning where practical, and keep existing project progress fallback.
- Users may expect `interrupted` tasks to resume automatically → UI copy and task status details must state that only terminal summaries are recovered and running work must be restarted.
- Persisting `params_summary` may include local paths or user inputs already visible in current task records → keep the scope to existing task response data and do not add secrets to summaries.
- Minimal terminal events are not full replay → document this boundary in specs and tasks so a later event-replay change can extend it deliberately.

## Migration Plan

1. Add the task-summary store with tolerant loading; no migration is required for old workspaces.
2. Start writing summaries for newly started tasks and terminal transitions.
3. Update project response logic to prefer loaded runtime summaries when `latest_task_id` exists.
4. Update frontend status labels and task surfaces for `interrupted`.

Rollback is straightforward: old code ignores `workspace/task_summaries/` files. Existing project metadata remains compatible.

## Open Questions

无。完整事件回放、SSE heartbeat 和自动恢复 running task 明确保留为后续 change。
