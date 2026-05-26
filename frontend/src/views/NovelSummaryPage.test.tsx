import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import { MAX_UPLOAD_FILE_BYTES } from "../api/uploadLimits";
import { AppStateProvider } from "../state/AppState";
import { NovelSummaryPage } from "./NovelSummaryPage";

describe("NovelSummaryPage", () => {
  beforeEach(() => {
    vi.spyOn(apiClient, "listProjects").mockResolvedValue([]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("rejects oversized source files before reading file contents", async () => {
    const arrayBuffer = vi.fn();
    const oversizedFile = {
      name: "huge-novel.txt",
      size: MAX_UPLOAD_FILE_BYTES + 1,
      arrayBuffer
    } as unknown as File;

    render(
      <AppStateProvider>
        <NovelSummaryPage />
      </AppStateProvider>
    );

    const sourceUploadLabel = screen.getByText(/拖拽 \.txt 文件到此处或点击选择/).closest("label");
    const sourceInput = sourceUploadLabel?.querySelector("input");
    expect(sourceInput).not.toBeNull();

    fireEvent.change(sourceInput as HTMLInputElement, {
      target: { files: [oversizedFile] }
    });

    await waitFor(() => {
      expect(screen.getByText(/超过 100 MB 上传限制/)).toBeInTheDocument();
    });
    expect(arrayBuffer).not.toHaveBeenCalled();
    expect(screen.queryByText("huge-novel.txt")).not.toBeInTheDocument();
  });
});
