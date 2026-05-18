import { useEffect } from "react";
import { apiClient } from "../api/client";
import { useAppState } from "../state/AppState";

export function useBootstrapData() {
  const { dispatch } = useAppState();

  useEffect(() => {
    let isMounted = true;
    dispatch({ type: "set_loading_config", value: true });

    Promise.all([apiClient.loadApiConfigs(), apiClient.loadPrompts()])
      .then(([apiConfigs, prompts]) => {
        if (!isMounted) {
          return;
        }
        dispatch({ type: "set_api_configs", items: apiConfigs });
        dispatch({ type: "set_prompts", items: prompts });
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
  }, [dispatch]);
}
