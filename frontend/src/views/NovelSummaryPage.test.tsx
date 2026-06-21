import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import type { ApiConfig, ProjectRecord, TaskRecord } from "../api/types";
import { MAX_UPLOAD_FILE_BYTES } from "../api/uploadLimits";
import { AppStateProvider, useAppState } from "../state/AppState";
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
    const splitChapter = makeUploadedFile("split-1", "第001章.txt");
    const updatedProject = makeProjectRecord({
      uploads: [splitChapter],
      upload_count: 1
    });
    const splitAndIngestSource = vi.spyOn(apiClient, "splitAndIngestSource").mockResolvedValue(updatedProject);
    vi.spyOn(apiClient, "uploadTextFiles").mockResolvedValue({
      project,
      items: [uploadedFile],
      workflow_output_directory: project.default_output_directory
    });
    vi.spyOn(apiClient, "saveProject").mockResolvedValue(project);
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
      expect(splitAndIngestSource).toHaveBeenCalledWith({
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
    await waitFor(() => {
      expect(screen.getByText("第001章.txt")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.queryByText("source.txt")).not.toBeInTheDocument();
    });
    expect(screen.queryByText("分割预览")).not.toBeInTheDocument();
  });

  it("creates a project from source split when no chapter files were uploaded first", async () => {
    const splitChapter = makeUploadedFile("split-1", "第001章.txt");
    const updatedProject = makeProjectRecord({
      project_name: "Only Source",
      project_slug: "Only_Source",
      uploads: [splitChapter],
      upload_count: 1
    });
    const splitAndIngestSource = vi.spyOn(apiClient, "splitAndIngestSource").mockResolvedValue(updatedProject);
    const saveProject = vi.spyOn(apiClient, "saveProject");
    vi.spyOn(apiClient, "previewSplit").mockResolvedValue({
      chapter_count: 1,
      chapters: [{ index: 1, title: "第一章", line_number: 1, word_count: 4 }]
    });

    render(
      <AppStateProvider>
        <NovelSummaryPage />
      </AppStateProvider>
    );

    const projectNameInput = screen.getByText("项目名称").closest("label")?.querySelector("input");
    expect(projectNameInput).not.toBeNull();
    fireEvent.change(projectNameInput as HTMLInputElement, {
      target: { value: "Only Source" }
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
      expect(splitAndIngestSource).toHaveBeenCalledWith({
        source_txt_file_path: "",
        output_directory_path: "",
        file_content: "第一章 正文",
        mode: "default",
        custom_pattern: "",
        title_list: [],
        handle_volumes: true,
        context: "novel_summary",
        pattern_config_id: undefined,
        project_name: "Only Source",
        project_slug: undefined,
        uploaded_file_ids: []
      });
    });
    expect(saveProject).not.toHaveBeenCalled();
    expect(screen.getByText("第001章.txt")).toBeInTheDocument();
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
    vi.spyOn(apiClient, "splitAndIngestSource").mockRejectedValue(new Error("未匹配到任何章节"));
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

  it("shows terminal project state and warnings after restoring history", async () => {
    const project = makeProjectRecord({
      latest_task_status: "partial_failed",
      uploads: [
        {
          id: "chapter-1",
          project_slug: "demo",
          original_name: "chapter.txt",
          stored_name: "chapter.txt",
          path: "workspace/demo/chapter.txt",
          size: 7,
          uploaded_at: 1
        }
      ],
      upload_count: 1,
      warnings: ["部分章节总结失败，已保留可用结果。"]
    });
    vi.spyOn(apiClient, "listProjects").mockResolvedValue([project]);
    vi.spyOn(apiClient, "getProject").mockResolvedValue(project);

    render(
      <AppStateProvider>
        <SeedState apiConfigs={[makeApiConfig()]}>
          <NovelSummaryPage />
        </SeedState>
      </AppStateProvider>
    );

    await screen.findByText("Demo");
    fireEvent.click(screen.getByText("Demo"));

    await waitFor(() => {
      expect(screen.getAllByText("部分结果").length).toBeGreaterThan(0);
    });
    expect(screen.getByText("最近任务：partial_failed")).toBeInTheDocument();
    expect(screen.getByText("部分章节总结失败，已保留可用结果。")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^开始$/ })).not.toBeDisabled();
    });
  });

  it("renders large restored chapter lists incrementally", async () => {
    const uploads = Array.from({ length: 140 }, (_, index) =>
      makeUploadedFile(`chapter-${index + 1}`, `chapter-${String(index + 1).padStart(3, "0")}.txt`)
    );
    const project = makeProjectRecord({
      uploads,
      upload_count: uploads.length
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
      expect(screen.getByText("chapter-001.txt")).toBeInTheDocument();
    });
    expect(screen.getByText("已显示 80 / 140 个文件")).toBeInTheDocument();
    expect(screen.queryByText("chapter-140.txt")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /再显示/ }));

    await waitFor(() => {
      expect(screen.getByText("chapter-140.txt")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "收起列表" }));

    await waitFor(() => {
      expect(screen.queryByText("chapter-140.txt")).not.toBeInTheDocument();
    });
  });

  it("collapses long reconciliation warnings into compact summaries", async () => {
    const warnings = Array.from({ length: 6 }, (_, index) => ({
      code: "missing_output",
      message: `缺失输出 ${index + 1}`,
      severity: "warning",
      paths: []
    }));
    const checks = warnings.map((warning, index) => ({
      id: `check-${index + 1}`,
      label: `输出检查 ${index + 1}`,
      status: "missing",
      expected: `exports/demo/output-${index + 1}.md`,
      actual: "",
      message: warning.message
    }));
    const project = makeProjectRecord({
      latest_task_status: "success",
      reconciliation_status: "abnormal_completed",
      reconciliation_warnings: warnings,
      output_checks: checks,
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
            required_inputs: ["chapter_files", "api_config", "summary_settings"],
            affected_outputs: ["输出 1", "输出 2", "输出 3", "输出 4", "输出 5"],
            repair_kind: "summary_content_regeneration",
            requires_llm: true,
            may_overwrite: false,
            may_change_content: true,
            estimated_scope: "missing_intermediates"
          }
        ]
      },
      warnings: warnings.map((warning) => warning.message)
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
    expect(screen.getByText("6 条产物警告")).toBeInTheDocument();
    expect(screen.getByText("查看全部警告")).toBeInTheDocument();
    expect(screen.getByText("6 项输出检查未通过，下面显示优先处理项。")).toBeInTheDocument();
    expect(screen.getByText("查看全部 6 项输出检查")).toBeInTheDocument();
    expect(screen.getByText("影响：输出 1、输出 2、输出 3 等 5 项")).toBeInTheDocument();
    expect(screen.getByText("查看全部影响输出")).toBeInTheDocument();
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

function SeedState({
  children,
  apiConfigs = []
}: {
  children: ReactNode;
  apiConfigs?: ApiConfig[];
}) {
  const { dispatch } = useAppState();
  useEffect(() => {
    if (apiConfigs.length > 0) {
      dispatch({ type: "set_api_configs", items: apiConfigs });
    }
  }, [apiConfigs, dispatch]);

  return <>{children}</>;
}

function makeApiConfig(): ApiConfig {
  return {
    id: "api-1",
    display_name: "API 1",
    url: "http://example.test/v1",
    key: "",
    model: "model",
    max_tokens: 4096,
    temperature: 0.7,
    stream: false,
    timeout: 30,
    max_retries: 3,
    is_active: true,
    key_env_var: ""
  };
}

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

function makeUploadedFile(id: string, name: string) {
  return {
    id,
    project_slug: "demo",
    original_name: name,
    stored_name: name,
    path: `workspace/demo/${name}`,
    size: 7,
    uploaded_at: 1
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
