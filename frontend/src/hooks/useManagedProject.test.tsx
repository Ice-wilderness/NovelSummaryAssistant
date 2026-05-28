import type { ReactNode } from "react";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import { MAX_UPLOAD_FILE_BYTES } from "../api/uploadLimits";
import type { ProjectRecord } from "../api/types";
import { AppStateProvider } from "../state/AppState";
import { useManagedProject } from "./useManagedProject";

function wrapper({ children }: { children: ReactNode }) {
  return <AppStateProvider>{children}</AppStateProvider>;
}

function project(overrides: Partial<ProjectRecord> = {}): ProjectRecord {
  return {
    project_name: "demo",
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

  it("keeps invalid output directory visible when backend validation fails", async () => {
    const uploadedProject = project({
      uploads: [
        {
          id: "file-1",
          project_slug: "demo",
          original_name: "a.txt",
          stored_name: "a.txt",
          path: "workspace/a.txt",
          size: 1,
          uploaded_at: 1
        }
      ],
      upload_count: 1
    });
    vi.spyOn(apiClient, "uploadTextFiles").mockResolvedValue({
      project: uploadedProject,
      items: uploadedProject.uploads,
      workflow_output_directory: "exports/demo"
    });
    vi.spyOn(apiClient, "checkOutputMigration").mockRejectedValue(
      new Error("输出目录不存在，请选择已有目录或使用默认输出目录")
    );
    const saveSpy = vi.spyOn(apiClient, "saveProject");
    const file = {
      name: "a.txt",
      size: 1,
      arrayBuffer: vi.fn().mockResolvedValue(new Uint8Array([97]).buffer)
    } as unknown as File;
    const { result } = renderHook(() => useManagedProject("novel_summary"), { wrapper });

    await act(async () => {
      await result.current.uploadFiles([file]);
    });
    act(() => {
      result.current.setOutputDirectory("missing-output");
    });
    await act(async () => {
      await result.current.saveProject();
    });

    expect(result.current.outputDirectory).toBe("missing-output");
    expect(result.current.outputDirectoryError).toContain("输出目录不存在");
    expect(saveSpy).not.toHaveBeenCalled();
  });

  it("clears custom output directory only after default fallback action", async () => {
    const customProject = project({
      custom_output_directory: "custom-output"
    });
    const defaultProject = project();
    vi.spyOn(apiClient, "uploadTextFiles").mockResolvedValue({
      project: customProject,
      items: [],
      workflow_output_directory: "exports/demo"
    });
    vi.spyOn(apiClient, "useDefaultOutputDirectory").mockResolvedValue(defaultProject);
    const file = {
      name: "a.txt",
      size: 1,
      arrayBuffer: vi.fn().mockResolvedValue(new Uint8Array([97]).buffer)
    } as unknown as File;
    const { result } = renderHook(() => useManagedProject("novel_summary"), { wrapper });

    await act(async () => {
      await result.current.uploadFiles([file]);
    });
    act(() => {
      result.current.setOutputDirectoryError("输出目录不存在");
    });
    await act(async () => {
      await result.current.useDefaultOutputDirectory();
    });

    expect(apiClient.useDefaultOutputDirectory).toHaveBeenCalledWith("demo");
    expect(result.current.outputDirectory).toBe("exports/demo");
    expect(result.current.outputDirectoryError).toBe("");
  });

  it("stores open output directory failures next to the output directory control", async () => {
    const uploadedProject = project();
    vi.spyOn(apiClient, "uploadTextFiles").mockResolvedValue({
      project: uploadedProject,
      items: [],
      workflow_output_directory: "exports/demo"
    });
    vi.spyOn(apiClient, "openDirectory").mockRejectedValue(new Error("目录不存在"));
    const file = {
      name: "a.txt",
      size: 1,
      arrayBuffer: vi.fn().mockResolvedValue(new Uint8Array([97]).buffer)
    } as unknown as File;
    const { result } = renderHook(() => useManagedProject("novel_summary"), { wrapper });

    await act(async () => {
      await result.current.uploadFiles([file]);
    });
    await act(async () => {
      await result.current.openOutputDirectory();
    });

    expect(result.current.outputDirectoryError).toBe("目录不存在");
  });
});
