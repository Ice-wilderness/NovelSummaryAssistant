import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import type { ProjectRecord, TaskRecord } from "../api/types";
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

  it("shows split-and-ingest failures without clearing source or chapter state", async () => {
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
    vi.spyOn(apiClient, "startSplitter").mockRejectedValue(new Error("未匹配到任何章节"));
    vi.spyOn(apiClient, "uploadTextFiles").mockResolvedValue({
      project,
      items: [uploadedFile],
      workflow_output_directory: project.default_output_directory
    });
    vi.spyOn(apiClient, "saveProject").mockResolvedValue(project);
    const getProject = vi.spyOn(apiClient, "getProject").mockResolvedValue(project);
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
      target: { files: [new File(["没有章节标题"], "source.txt", { type: "text/plain" })] }
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
      expect(screen.getByText("分割失败：未匹配到任何章节")).toBeInTheDocument();
    });
    expect(screen.getByText("source.txt")).toBeInTheDocument();
    expect(screen.getByText("chapter.txt")).toBeInTheDocument();
    expect(getProject).not.toHaveBeenCalled();
  });

  it("shows abnormal project warnings and repair actions after restoring history", async () => {
    const project = makeProjectRecord({
      latest_task_status: "success",
      reconciliation_status: "abnormal_completed",
      reconciliation_warnings: [
        {
          code: "missing_output",
          message: "终极剧情总结 P1 缺失",
          severity: "warning",
          paths: ["exports/demo/.summarizer_cache/终极剧情"]
        }
      ],
      output_checks: [
        {
          id: "ultimate_plot_p1",
          label: "终极剧情总结 P1",
          status: "missing",
          expected: "exports/demo/.summarizer_cache/终极剧情/*.md",
          actual: "",
          message: "未找到对应输出文件"
        }
      ],
      repair_plan: {
        project_slug: "demo",
        status: "abnormal_completed",
        actions: [
          {
            action_id: "rerun_missing_summary_stages",
            label: "补跑缺失总结阶段",
            description: "从现有章节继续运行小说总结流程，补齐缺失总结正文。",
            status: "available",
            blocked_reason: "",
            required_inputs: ["chapter_files", "api_config"],
            affected_outputs: ["终极剧情总结 P1"],
            repair_kind: "summary_content_regeneration",
            requires_llm: true,
            may_overwrite: false,
            may_change_content: true,
            estimated_scope: "missing_intermediates"
          },
          {
            action_id: "blocked_repair",
            label: "不可修复动作",
            description: "缺少章节文件。",
            status: "blocked",
            blocked_reason: "输出目录中没有可用章节 TXT 文件。",
            required_inputs: ["chapter_files"],
            affected_outputs: [],
            repair_kind: "summary_content_regeneration",
            requires_llm: true,
            may_overwrite: false,
            may_change_content: true,
            estimated_scope: "missing_intermediates"
          }
        ]
      },
      warnings: ["终极剧情总结 P1 缺失"]
    });
    vi.spyOn(apiClient, "listProjects").mockResolvedValue([project]);
    vi.spyOn(apiClient, "getProject").mockResolvedValue(project);

    render(
      <AppStateProvider>
        <NovelSummaryPage />
      </AppStateProvider>
    );

    await screen.findByText("Demo");
    fireEvent.click(screen.getByText("Demo"));

    await waitFor(() => {
      expect(screen.getByLabelText("项目修复建议")).toBeInTheDocument();
    });
    expect(screen.getAllByText("异常完成").length).toBeGreaterThan(0);
    expect(screen.getByText(/当前问题是已完成记录对应的输出产物缺失或不一致/)).toBeInTheDocument();
    expect(screen.getAllByText("终极剧情总结 P1 缺失").length).toBeGreaterThan(0);
    expect(screen.getByText("终极剧情总结 P1")).toBeInTheDocument();
    expect(screen.getByText("补跑缺失总结阶段")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /执行修复/ })).toBeInTheDocument();
    expect(screen.getByText("不可修复动作")).toBeInTheDocument();
    expect(screen.getByText("输出目录中没有可用章节 TXT 文件。")).toBeInTheDocument();
  });

  it("confirms LLM repair before starting and refreshes project state", async () => {
    const project = makeRepairableProject();
    const startProjectRepair = vi
      .spyOn(apiClient, "startProjectRepair")
      .mockResolvedValue(makeTaskRecord({ status: "success" }));
    vi.spyOn(apiClient, "listProjects").mockResolvedValue([project]);
    const getProject = vi.spyOn(apiClient, "getProject").mockResolvedValue(project);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <AppStateProvider>
        <NovelSummaryPage />
      </AppStateProvider>
    );

    await screen.findByText("Demo");
    fireEvent.click(screen.getByText("Demo"));
    await screen.findByText("补跑缺失总结阶段");
    fireEvent.click(screen.getByRole("button", { name: /执行修复/ }));

    await waitFor(() => {
      expect(startProjectRepair).toHaveBeenCalledWith(
        "demo",
        expect.objectContaining({
          action_id: "rerun_missing_summary_stages",
          confirm_llm: true,
          confirm_content_change: true,
          confirm_overwrite: undefined
        })
      );
    });
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("可能调用 LLM"));
    expect(getProject.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("shows repair validation errors and refreshes the project", async () => {
    const project = makeRepairableProject();
    vi.spyOn(apiClient, "listProjects").mockResolvedValue([project]);
    const getProject = vi.spyOn(apiClient, "getProject").mockResolvedValue(project);
    vi.spyOn(apiClient, "startProjectRepair").mockRejectedValue(new Error("修复计划已过期，请刷新项目状态后重试。"));
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <AppStateProvider>
        <NovelSummaryPage />
      </AppStateProvider>
    );

    await screen.findByText("Demo");
    fireEvent.click(screen.getByText("Demo"));
    await screen.findByText("补跑缺失总结阶段");
    fireEvent.click(screen.getByRole("button", { name: /执行修复/ }));

    await waitFor(() => {
      expect(screen.getByText("修复计划已过期，请刷新项目状态后重试。")).toBeInTheDocument();
    });
    expect(getProject).toHaveBeenCalledTimes(2);
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

function makeRepairableProject(): ProjectRecord {
  return makeProjectRecord({
    latest_task_status: "success",
    reconciliation_status: "abnormal_completed",
    reconciliation_warnings: [
      {
        code: "missing_output",
        message: "终极剧情总结 P1 缺失",
        severity: "warning",
        paths: []
      }
    ],
    output_checks: [
      {
        id: "ultimate_plot_p1",
        label: "终极剧情总结 P1",
        status: "missing",
        expected: "exports/demo/.summarizer_cache/终极剧情/*.md",
        actual: "",
        message: "未找到对应输出文件"
      }
    ],
    repair_plan: {
      project_slug: "demo",
      status: "abnormal_completed",
      actions: [
        {
          action_id: "rerun_missing_summary_stages",
          label: "补跑缺失总结阶段",
          description: "从现有章节继续运行小说总结流程，补齐缺失总结正文。",
          status: "available",
          blocked_reason: "",
          required_inputs: ["chapter_files", "api_config"],
          affected_outputs: ["终极剧情总结 P1"],
          repair_kind: "summary_content_regeneration",
          requires_llm: true,
          may_overwrite: false,
          may_change_content: true,
          estimated_scope: "missing_intermediates"
        }
      ]
    },
    warnings: ["终极剧情总结 P1 缺失"]
  });
}

function makeTaskRecord(overrides: Partial<TaskRecord> = {}): TaskRecord {
  return {
    task_id: "repair-task",
    task_type: "project_repair",
    status: "running",
    progress_text: "",
    created_at: 1,
    updated_at: 1,
    finished_at: null,
    result_summary: null,
    error: null,
    warnings: [],
    result_data: {},
    params_summary: { project_slug: "demo" },
    events: [],
    ...overrides
  };
}
