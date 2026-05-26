import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import type { ProjectRecord } from "../api/types";
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

  it("starts split-and-ingest through apiClient and clears source state after success", async () => {
    const uploadedFile = {
      id: "upload-1",
      project_slug: "demo",
      original_name: "chapter.txt",
      stored_name: "chapter.txt",
      path: "workspace/demo/chapter.txt",
      size: 7,
      uploaded_at: 1
    };
    const project = makeProjectRecord({
      uploads: [uploadedFile],
      upload_count: 1
    });
    const startSplitter = vi.spyOn(apiClient, "startSplitter").mockResolvedValue({} as never);
    vi.spyOn(apiClient, "uploadTextFiles").mockResolvedValue({
      project,
      items: [uploadedFile],
      workflow_output_directory: project.default_output_directory
    });
    vi.spyOn(apiClient, "saveProject").mockResolvedValue(project);
    vi.spyOn(apiClient, "getProject").mockResolvedValue(project);
    vi.spyOn(apiClient, "previewSplit").mockResolvedValue({
      chapter_count: 1,
      chapters: [{ index: 1, title: "第一章", line_number: 1, word_count: 4 }]
    });

    render(
      <AppStateProvider>
        <NovelSummaryPage />
      </AppStateProvider>
    );

    const chapterInput = screen.getByLabelText("章节文件").querySelector("input");
    expect(chapterInput).not.toBeNull();
    fireEvent.change(chapterInput as HTMLInputElement, {
      target: { files: [new File(["chapter"], "chapter.txt", { type: "text/plain" })] }
    });
    await waitFor(() => {
      expect(apiClient.uploadTextFiles).toHaveBeenCalled();
    });

    const sourceInput = screen
      .getByText(/拖拽 \.txt 文件到此处或点击选择/)
      .closest("label")
      ?.querySelector("input");
    expect(sourceInput).not.toBeNull();
    fireEvent.change(sourceInput as HTMLInputElement, {
      target: { files: [new File(["第一章 正文"], "source.txt", { type: "text/plain" })] }
    });
    await waitFor(() => {
      expect(screen.getByText("source.txt")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /预览分割/ }));
    await waitFor(() => {
      expect(screen.getByText("分割预览")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /确认分割/ }));

    await waitFor(() => {
      expect(startSplitter).toHaveBeenCalledWith({
        source_txt_file_path: "",
        output_directory_path: "",
        file_content: "第一章 正文",
        mode: "default",
        custom_pattern: "",
        title_list: [],
        handle_volumes: true,
        context: "novel_summary",
        pattern_config_id: undefined,
        project_name: "Demo",
        project_slug: "demo",
        uploaded_file_ids: []
      });
    });
    expect(apiClient.getProject).toHaveBeenCalledWith("demo");
    await waitFor(() => {
      expect(screen.queryByText("source.txt")).not.toBeInTheDocument();
    });
    expect(screen.queryByText("分割预览")).not.toBeInTheDocument();
  });
});

function makeProjectRecord(overrides: Partial<ProjectRecord> = {}): ProjectRecord {
  return {
    project_name: "Demo",
    project_slug: "demo",
    workflow_type: "novel_summary",
    default_output_directory: "exports/demo",
    custom_output_directory: "",
    summary_batch_size: 10,
    summary_output_format: "md",
    use_fine_grained_flow: false,
    requires_granularity_migration: false,
    legacy_grouped_file_count: 0,
    granularity_migration_backup_path: "",
    uploads: [],
    upload_count: 0,
    latest_task_id: "",
    latest_task_status: "",
    imported_from_path: "",
    progress: {
      workflow_type: "novel_summary",
      summary: "",
      percent: 0,
      stages: []
    },
    created_at: 1,
    updated_at: 1,
    warnings: [],
    ...overrides
  };
}
