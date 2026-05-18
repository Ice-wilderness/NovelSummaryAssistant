import { useMemo } from "react";
import { useAppState } from "../state/AppState";

const busyStatuses = new Set(["pending", "running", "paused", "canceling"]);

export function useTaskAvailability() {
  const { state } = useAppState();
  return useMemo(() => {
    const latestTask = state.taskOrder.length > 0 ? state.tasks[state.taskOrder[0]] : null;
    return {
      latestTask,
      isTaskBusy: Boolean(latestTask && busyStatuses.has(latestTask.status))
    };
  }, [state.taskOrder, state.tasks]);
}
