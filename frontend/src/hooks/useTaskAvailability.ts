import { useMemo } from "react";
import type { TaskRecord } from "../api/types";
import { useAppState } from "../state/AppState";

const busyStatuses = new Set(["pending", "running", "paused", "canceling"]);

export function useTaskAvailability() {
  const { state } = useAppState();
  return useMemo(() => {
    const sessionTasks = state.sessionTaskIds
      .map((taskId) => state.tasks[taskId])
      .filter((task): task is TaskRecord => Boolean(task));
    const latestTask = sessionTasks[0] ?? null;
    return {
      latestTask,
      isTaskBusy: sessionTasks.some((task) => busyStatuses.has(task.status))
    };
  }, [state.sessionTaskIds, state.tasks]);
}
