import { apiClient } from "../api/client";
import { useAppState } from "../state/AppState";

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

export function usePathPicker() {
  const { dispatch } = useAppState();

  const pickDirectory = async (
    title: string,
    onPick: (path: string) => void,
    onError?: (message: string) => void
  ) => {
    try {
      const path = await apiClient.pickDirectory(title);
      if (path) {
        onPick(path);
      }
      onError?.("");
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      const message = errorMessage(error);
      onError?.(message);
      dispatch({ type: "set_error", message });
    }
  };

  const pickFile = async (
    title: string,
    onPick: (path: string) => void,
    onError?: (message: string) => void
  ) => {
    try {
      const path = await apiClient.pickFile(title);
      if (path) {
        onPick(path);
      }
      onError?.("");
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      const message = errorMessage(error);
      onError?.(message);
      dispatch({ type: "set_error", message });
    }
  };

  return { pickDirectory, pickFile };
}
