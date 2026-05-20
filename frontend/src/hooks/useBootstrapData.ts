import { useEffect } from "react";
import { apiClient } from "../api/client";
import { useAppState } from "../state/AppState";
import { useTaskActions } from "./useTaskActions";

export function useBootstrapData() {
  const { dispatch } = useAppState();
  const { watchTask } = useTaskActions();

  useEffect(() => {
    let isMounted = true;
    dispatch({ type: "set_loading_config", value: true });

    Promise.all([
      apiClient.loadApiConfigs(),
      apiClient.loadUserSettings(),
      apiClient.loadPromptConfig(),
      apiClient.listTasks()
    ])
      .then(([apiConfigs, userSettings, promptResponse, tasks]) => {
        if (!isMounted) {
          return;
        }
        dispatch({ type: "set_api_configs", items: apiConfigs });
        dispatch({ type: "set_user_settings", settings: userSettings });
        dispatch({ type: "set_prompts", items: promptResponse.items });
        dispatch({
          type: "set_workflow_prompt_config",
          config: promptResponse.workflow_config
        });
        dispatch({ type: "restore_tasks", items: tasks });
        tasks.forEach((task) => watchTask(task));
        dispatch({ type: "set_error", message: null });
      })
      .catch((error: unknown) => {
        if (isMounted) {
          dispatch({
            type: "set_error",
            message: error instanceof Error ? error.message : String(error)
          });
        }
      })
      .finally(() => {
        if (isMounted) {
          dispatch({ type: "set_loading_config", value: false });
        }
      });

    return () => {
      isMounted = false;
    };
  }, [dispatch, watchTask]);
}
