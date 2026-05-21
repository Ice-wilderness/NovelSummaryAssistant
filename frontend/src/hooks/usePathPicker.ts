import { apiClient } from "../api/client";
import { useAppState } from "../state/AppState";

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

export function usePathPicker() {
  const { dispatch } = useAppState();

  const pickDirectory = async (title: string, onPick: (path: string) => void) => {
    try {
      const path = await apiClient.pickDirectory(title);
      if (path) {
        onPick(path);
      }
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      dispatch({ type: "set_error", message: errorMessage(error) });
    }
  };

  const pickFile = async (title: string, onPick: (path: string) => void) => {
    try {
      const path = await apiClient.pickFile(title);
      if (path) {
        onPick(path);
      }
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      dispatch({ type: "set_error", message: errorMessage(error) });
    }
  };

  return { pickDirectory, pickFile };
}
