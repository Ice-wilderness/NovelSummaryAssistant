import { apiClient } from "../api/client";
import type { BrowseFileType } from "../api/types";
import { useAppState } from "../state/AppState";

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

export function appendImportedPaths(currentText: string, paths: string[]) {
  const currentLines = currentText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const nextLines = [...currentLines];
  paths
    .map((path) => path.trim())
    .filter(Boolean)
    .forEach((path) => {
      if (!nextLines.includes(path)) {
        nextLines.push(path);
      }
    });
  return nextLines.join("\n");
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

  const pickFile = async (
    title: string,
    filetypes: BrowseFileType[],
    onPick: (path: string) => void
  ) => {
    try {
      const path = await apiClient.pickFile(title, filetypes);
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
