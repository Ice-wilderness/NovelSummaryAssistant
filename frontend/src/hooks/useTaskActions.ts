import { useCallback } from "react";
import { apiClient, subscribeTaskEvents, type TaskEventSubscription } from "../api/client";
import type { TaskEvent, TaskRecord } from "../api/types";
import { useAppState } from "../state/AppState";

const subscriptions = new Map<string, TaskEventSubscription>();
const terminalStatuses = new Set(["cancelled", "success", "failed"]);

function eventIsTerminal(event: TaskEvent) {
  return Boolean(event.status && terminalStatuses.has(String(event.status)));
}

function taskIsTerminal(task: TaskRecord) {
  return terminalStatuses.has(task.status);
}

interface TaskActionOptions {
  onTaskTerminal?: (task: TaskRecord) => void;
}

export function useTaskActions(options: TaskActionOptions = {}) {
  const { dispatch } = useAppState();
  const { onTaskTerminal } = options;

  const watchTask = useCallback(
    (task: TaskRecord) => {
      dispatch({ type: "upsert_task", task });
      if (taskIsTerminal(task)) {
        subscriptions.get(task.task_id)?.close();
        subscriptions.delete(task.task_id);
        onTaskTerminal?.(task);
        return;
      }
      if (subscriptions.has(task.task_id)) {
        return;
      }
      const subscription = subscribeTaskEvents(task.task_id, {
        onEvent: (event) => {
          dispatch({ type: "append_event", event });
          if (eventIsTerminal(event)) {
            apiClient
              .getTask(event.task_id)
              .then((latestTask) => {
                dispatch({ type: "upsert_task", task: latestTask });
                onTaskTerminal?.(latestTask);
              })
              .catch(() => undefined);
            subscriptions.get(event.task_id)?.close();
            subscriptions.delete(event.task_id);
          }
        },
        onError: () => {
          dispatch({ type: "set_error", message: "任务事件流连接中断" });
        }
      });
      subscriptions.set(task.task_id, subscription);
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
