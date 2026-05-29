import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { usePersistentSplitSettings } from "./usePersistentSplitSettings";

describe("usePersistentSplitSettings", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("persists the preferred split mode and regex config", () => {
    const { result, unmount } = renderHook(() => usePersistentSplitSettings());

    act(() => {
      result.current.setMode("regex");
      result.current.setSelectedPatternId("custom-pattern");
      result.current.setHandleVolumes(false);
    });

    unmount();

    const restored = renderHook(() => usePersistentSplitSettings());

    expect(restored.result.current.mode).toBe("regex");
    expect(restored.result.current.selectedPatternId).toBe("custom-pattern");
    expect(restored.result.current.handleVolumes).toBe(false);
  });

  it("falls back to defaults when saved settings are invalid", () => {
    window.localStorage.setItem(
      "studio.chapterSplitSettings.v1",
      JSON.stringify({ handleVolumes: "yes", mode: "unknown", selectedPatternId: 123 })
    );

    const { result } = renderHook(() => usePersistentSplitSettings());

    expect(result.current.mode).toBe("default");
    expect(result.current.selectedPatternId).toBe("");
    expect(result.current.handleVolumes).toBe(true);
  });
});
