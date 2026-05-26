import type { ReactNode } from "react";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import { MAX_UPLOAD_FILE_BYTES } from "../api/uploadLimits";
import { AppStateProvider } from "../state/AppState";
import { useManagedProject } from "./useManagedProject";

function wrapper({ children }: { children: ReactNode }) {
  return <AppStateProvider>{children}</AppStateProvider>;
}

describe("useManagedProject", () => {
  beforeEach(() => {
    vi.spyOn(apiClient, "listProjects").mockResolvedValue([]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("rejects oversized uploads before reading file contents", async () => {
    const arrayBuffer = vi.fn();
    const uploadSpy = vi.spyOn(apiClient, "uploadTextFiles");
    const oversizedFile = {
      name: "oversized.txt",
      size: MAX_UPLOAD_FILE_BYTES + 1,
      arrayBuffer
    } as unknown as File;
    const { result } = renderHook(() => useManagedProject("novel_summary"), { wrapper });

    await act(async () => {
      await result.current.uploadFiles([oversizedFile]);
    });

    expect(arrayBuffer).not.toHaveBeenCalled();
    expect(uploadSpy).not.toHaveBeenCalled();
    expect(result.current.error).toContain("100 MB");
  });
});
