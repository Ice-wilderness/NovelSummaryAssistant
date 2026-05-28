import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ProjectRecord } from "../../api/types";
import { OutputDirectoryField, ProjectHistoryField } from "./FormControls";

function project(overrides: Partial<ProjectRecord> = {}): ProjectRecord {
  return {
    project_name: "中断项目",
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
    latest_task_id: "task-1",
    latest_task_status: "interrupted",
    imported_from_path: "",
    progress: {
      workflow_type: "novel_summary",
      summary: "",
      percent: 0,
      stages: []
    },
    created_at: 1,
    updated_at: 2,
    warnings: [],
    ...overrides
  };
}

describe("ProjectHistoryField", () => {
  it("shows interrupted project status without rewriting it as failure", () => {
    render(
      <ProjectHistoryField
        projects={[project()]}
        value=""
        onDelete={vi.fn()}
        onNewProject={vi.fn()}
        onRestore={vi.fn()}
      />
    );

    expect(screen.getByText("已中断")).toBeInTheDocument();
    expect(screen.getByText("中断项目")).toBeInTheDocument();
    expect(screen.queryByText("失败")).not.toBeInTheDocument();
  });

  it("keeps persisted partial failed status display unchanged", () => {
    render(
      <ProjectHistoryField
        projects={[project({ latest_task_status: "partial_failed", project_name: "部分项目" })]}
        value=""
        onDelete={vi.fn()}
        onNewProject={vi.fn()}
        onRestore={vi.fn()}
      />
    );

    expect(screen.getByText("部分结果")).toBeInTheDocument();
    expect(screen.getByText("部分项目")).toBeInTheDocument();
  });

  it("shows abnormal completion without replacing the persisted task status", () => {
    render(
      <ProjectHistoryField
        projects={[
          project({
            latest_task_status: "success",
            project_name: "异常项目",
            reconciliation_status: "abnormal_completed",
            warnings: ["终极剧情总结缺失"]
          })
        ]}
        value=""
        onDelete={vi.fn()}
        onNewProject={vi.fn()}
        onRestore={vi.fn()}
      />
    );

    expect(screen.getByText("完成")).toBeInTheDocument();
    expect(screen.getByText("异常完成")).toBeInTheDocument();
    expect(screen.getByText("异常项目")).toBeInTheDocument();
  });
});

describe("OutputDirectoryField", () => {
  it("shows output directory errors near the control and exposes default fallback", () => {
    const onUseDefaultDirectory = vi.fn();

    render(
      <OutputDirectoryField
        defaultDirectory="exports/demo"
        error="输出目录不存在，请选择已有目录或使用默认输出目录"
        outputDirectory="missing"
        onBrowseOutputDirectory={vi.fn()}
        onOpenOutputDirectory={vi.fn()}
        onOutputDirectoryChange={vi.fn()}
        onUseDefaultDirectory={onUseDefaultDirectory}
        onValidateOutputDirectory={vi.fn()}
      />
    );

    expect(screen.getByText("输出目录不存在，请选择已有目录或使用默认输出目录")).toBeInTheDocument();

    fireEvent.click(screen.getByText("使用默认目录"));

    expect(onUseDefaultDirectory).toHaveBeenCalledOnce();
  });
});
