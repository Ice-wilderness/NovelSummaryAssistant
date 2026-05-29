import { useEffect, type ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import type { ApiConfig, ProjectRecord, TaskRecord } from "../api/types";
import { AppStateProvider, useAppState } from "../state/AppState";
import { ArticleSummaryPage } from "./ArticleSummaryPage";
import { CustomSummaryPage } from "./CustomSummaryPage";

const EMPTY_API_CONFIGS: ApiConfig[] = [];
const EMPTY_TASKS: TaskRecord[] = [];

function SeedState({
  children,
  apiConfigs = EMPTY_API_CONFIGS,
  tasks = EMPTY_TASKS
}: {
  children: ReactNode;
  apiConfigs?: ApiConfig[];
  tasks?: TaskRecord[];
}) {
  const { dispatch } = useAppState();
  useEffect(() => {
    if (apiConfigs.length > 0) {
      dispatch({ type: "set_api_configs", items: apiConfigs });
    }
    tasks.forEach((task) => dispatch({ type: "upsert_task", task }));
  }, [apiConfigs, dispatch, tasks]);

  return <>{children}</>;
}

describe("article and custom summary pages", () => {
  beforeEach(() => {
    vi.spyOn(apiClient, "listProjects").mockResolvedValue([]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows article partial results with failed section details and failed history state", async () => {
    vi.mocked(apiClient.listProjects).mockResolvedValue([
      makeProjectRecord({
        workflow_type: "article_summary",
        latest_task_status: "failed"
      })
    ]);

    render(
      <AppStateProvider>
        <SeedState
          tasks={[
            makeTaskRecord({
              task_type: "article_summary",
              status: "partial_failed",
              warnings: ["第 2 段总结失败，已保留最终结果。"],
              result_summary: "exports/article/final.md",
              result_data: {
                final_output_path: "exports/article/final.md",
                failed_sections: [{ filename: "part-2.txt", error: "API timeout" }]
              }
            })
          ]}
        >
          <ArticleSummaryPage />
        </SeedState>
      </AppStateProvider>
    );

    expect(await screen.findByText("文章总结部分结果")).toBeInTheDocument();
    expect(screen.getByText("第 2 段总结失败，已保留最终结果。")).toBeInTheDocument();
    expect(screen.getByText("part-2.txt：API timeout")).toBeInTheDocument();
    expect(screen.getByText("可用结果：exports/article/final.md")).toBeInTheDocument();
    expect(await screen.findByText("失败")).toBeInTheDocument();
  });

  it("shows custom partial results with failed source details and cancelled history state", async () => {
    vi.mocked(apiClient.listProjects).mockResolvedValue([
      makeProjectRecord({
        workflow_type: "custom_summary",
        latest_task_status: "cancelled"
      })
    ]);

    render(
      <AppStateProvider>
        <SeedState
          apiConfigs={[makeApiConfig()]}
          tasks={[
            makeTaskRecord({
              task_type: "custom_summary",
              status: "partial_failed",
              warnings: ["参考材料读取失败，已保留可用输出。"],
              result_summary: "保留正文",
              result_data: {
                output_text: "保留正文",
                failed_source_files: [{ source_file: "notes.txt", error: "文件缺失" }]
              }
            })
          ]}
        >
          <CustomSummaryPage />
        </SeedState>
      </AppStateProvider>
    );

    expect(await screen.findByText("自定义总结部分结果")).toBeInTheDocument();
    expect(screen.getByText("参考材料读取失败，已保留可用输出。")).toBeInTheDocument();
    expect(screen.getByText("notes.txt：文件缺失")).toBeInTheDocument();
    expect(screen.getAllByText("可用结果：保留正文").length).toBeGreaterThan(0);
    expect(await screen.findByText("已取消")).toBeInTheDocument();
  });
});

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
    workflow_type: "article_summary",
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
    latest_task_status: "failed",
    imported_from_path: "",
    progress: { workflow_type: "article_summary", summary: "", percent: 0, stages: [] },
    created_at: 1,
    updated_at: 1,
    warnings: [],
    ...overrides
  };
}

function makeTaskRecord(overrides: Partial<TaskRecord> = {}): TaskRecord {
  return {
    task_id: "task-1",
    task_type: "article_summary",
    status: "partial_failed",
    progress_text: "",
    created_at: 1,
    updated_at: 1,
    finished_at: 2,
    result_summary: "",
    error: null,
    warnings: [],
    result_data: {},
    params_summary: { project_slug: "demo" },
    events: [],
    ...overrides
  };
}
