import { useCallback } from "react";
import { apiClient, subscribeTaskEvents, type TaskEventSubscription } from "../api/client";
import type { TaskEvent, TaskRecord } from "../api/types";
import { useAppState } from "../state/AppState";

const subscriptions = new Map<string, TaskEventSubscription>();
const eventStreamErrorTimers = new Map<string, number>();
const latestEventIds = new Map<string, number>();
const processedEventIds = new Map<string, Set<number>>();
const terminalStatuses = new Set(["cancelled", "partial_failed", "success", "failed", "interrupted"]);
const EVENT_STREAM_ERROR_MESSAGE = "任务事件流连接中断";
const EVENT_STREAM_ERROR_DELAY_MS = 5000;

function eventIsTerminal(event: TaskEvent) {
  return Boolean(event.status && terminalStatuses.has(String(event.status)));
}

function taskIsTerminal(task: TaskRecord) {
  return terminalStatuses.has(task.status);
}

function clearEventStreamErrorTimer(taskId: string) {
  const timer = eventStreamErrorTimers.get(taskId);
  if (timer) {
    window.clearTimeout(timer);
    eventStreamErrorTimers.delete(taskId);
  }
}

function rememberTaskEvent(event: TaskEvent) {
  if (typeof event.event_id !== "number") {
    return true;
  }
  const seen = processedEventIds.get(event.task_id) ?? new Set<number>();
  if (seen.has(event.event_id)) {
    return false;
  }
  seen.add(event.event_id);
  processedEventIds.set(event.task_id, seen);
  const latestEventId = latestEventIds.get(event.task_id);
  if (latestEventId === undefined || event.event_id > latestEventId) {
    latestEventIds.set(event.task_id, event.event_id);
  }
  return true;
}

interface TaskActionOptions {
  onTaskTerminal?: (task: TaskRecord) => void;
}

export function useTaskActions(options: TaskActionOptions = {}) {
  const { dispatch } = useAppState();
  const { onTaskTerminal } = options;

  const watchTask = useCallback(
    (task: TaskRecord) => {
      const closeSubscription = (taskId: string) => {
        clearEventStreamErrorTimer(taskId);
        subscriptions.get(taskId)?.close();
        subscriptions.delete(taskId);
      };
      const scheduleConnectionError = (taskId: string) => {
        clearEventStreamErrorTimer(taskId);
        const timer = window.setTimeout(() => {
          eventStreamErrorTimers.delete(taskId);
          dispatch({ type: "set_error", message: EVENT_STREAM_ERROR_MESSAGE });
        }, EVENT_STREAM_ERROR_DELAY_MS);
        eventStreamErrorTimers.set(taskId, timer);
      };
      const refreshTask = async (taskId: string) => {
        const latestTask = await apiClient.getTask(taskId);
        dispatch({ type: "upsert_task", task: latestTask });
        if (taskIsTerminal(latestTask)) {
          closeSubscription(taskId);
          onTaskTerminal?.(latestTask);
        }
        return latestTask;
      };

      dispatch({ type: "upsert_task", task });
      if (taskIsTerminal(task)) {
        closeSubscription(task.task_id);
        onTaskTerminal?.(task);
        return;
      }
      if (subscriptions.has(task.task_id)) {
        return;
      }
      const openSubscription = () => {
        if (subscriptions.has(task.task_id)) {
          return;
        }
        const subscription = subscribeTaskEvents(
          task.task_id,
          {
            onEvent: (event) => {
              clearEventStreamErrorTimer(event.task_id);
              dispatch({ type: "clear_error_if", message: EVENT_STREAM_ERROR_MESSAGE });
              if (!rememberTaskEvent(event)) {
                return;
              }
              dispatch({ type: "append_event", event });
              if (eventIsTerminal(event)) {
                refreshTask(event.task_id).catch(() => undefined);
                closeSubscription(event.task_id);
              }
            },
            onHeartbeat: (heartbeatTaskId) => {
              clearEventStreamErrorTimer(heartbeatTaskId);
              dispatch({ type: "clear_error_if", message: EVENT_STREAM_ERROR_MESSAGE });
            },
            onReplayGap: (event) => {
              clearEventStreamErrorTimer(event.task_id);
              dispatch({ type: "clear_error_if", message: EVENT_STREAM_ERROR_MESSAGE });
              refreshTask(event.task_id).catch(() => undefined);
            },
            onError: () => {
              scheduleConnectionError(task.task_id);
              closeSubscription(task.task_id);
              refreshTask(task.task_id)
                .then((latestTask) => {
                  if (!taskIsTerminal(latestTask)) {
                    window.setTimeout(openSubscription, 250);
                  }
                })
                .catch(() => undefined);
            }
          },
          { lastEventId: latestEventIds.get(task.task_id) }
        );
        subscriptions.set(task.task_id, subscription);
      };
      openSubscription();
    },
    [dispatch, onTaskTerminal]
  );

  const startTask = useCallback(
    async (starter: () => Promise<TaskRecord>) => {
      try {
        const task = await starter();
        watchTask(task);
        dispatch({ type: "set_error", message: null });
        return task;
      } catch (error: unknown) {
        dispatch({
          type: "set_error",
          message: error instanceof Error ? error.message : String(error)
        });
        return null;
      }
    },
    [dispatch, watchTask]
  );

  return { startTask, watchTask };
}
