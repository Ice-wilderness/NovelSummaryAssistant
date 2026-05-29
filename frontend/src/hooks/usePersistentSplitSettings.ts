import { useEffect, useState } from "react";

export type SplitMode = "default" | "regex" | "title_list";

const STORAGE_KEY = "studio.chapterSplitSettings.v1";

interface StoredSplitSettings {
  handleVolumes?: unknown;
  mode?: unknown;
  selectedPatternId?: unknown;
}

interface SplitSettings {
  handleVolumes: boolean;
  mode: SplitMode;
  selectedPatternId: string;
}

const defaultSettings: SplitSettings = {
  handleVolumes: true,
  mode: "default",
  selectedPatternId: ""
};

function isSplitMode(value: unknown): value is SplitMode {
  return value === "default" || value === "regex" || value === "title_list";
}

function readSettings(): SplitSettings {
  if (typeof window === "undefined") {
    return defaultSettings;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return defaultSettings;
    }
    const parsed = JSON.parse(raw) as StoredSplitSettings;
    return {
      handleVolumes:
        typeof parsed.handleVolumes === "boolean"
          ? parsed.handleVolumes
          : defaultSettings.handleVolumes,
      mode: isSplitMode(parsed.mode) ? parsed.mode : defaultSettings.mode,
      selectedPatternId:
        typeof parsed.selectedPatternId === "string"
          ? parsed.selectedPatternId
          : defaultSettings.selectedPatternId
    };
  } catch {
    return defaultSettings;
  }
}

function saveSettings(settings: SplitSettings) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // Ignore storage failures; the page can still work with in-memory state.
  }
}

export function usePersistentSplitSettings() {
  const [initialSettings] = useState(readSettings);
  const [mode, setMode] = useState<SplitMode>(initialSettings.mode);
  const [handleVolumes, setHandleVolumes] = useState(initialSettings.handleVolumes);
  const [selectedPatternId, setSelectedPatternId] = useState(initialSettings.selectedPatternId);

  useEffect(() => {
    saveSettings({ handleVolumes, mode, selectedPatternId });
  }, [handleVolumes, mode, selectedPatternId]);

  return {
    handleVolumes,
    mode,
    selectedPatternId,
    setHandleVolumes,
    setMode,
    setSelectedPatternId
  };
}
