import { render, screen } from "@testing-library/react";
import { useEffect } from "react";
import { describe, expect, it } from "vitest";
import type { TaskRecord } from "../../api/types";
import { AppStateProvider, useAppState } from "../../state/AppState";
import { AppLayout } from "./AppLayout";

function task(overrides: Partial<TaskRecord> = {}): TaskRecord {
  return {
    task_id: "task-1",
    task_type: "novel_summary",
    status: "interrupted",
    progress_text: "处理中",
    created_at: 1,
    updated_at: 2,
    finished_at: 3,
    result_summary: null,
    error: "后端重启时任务仍未结束，无法自动恢复，请重新启动任务或从项目进度继续。",
    warnings: [],
    result_data: {},
    params_summary: {},
    events: [],
    ...overrides
  };
}

function SeedTask({ value }: { value: TaskRecord }) {
  const { dispatch } = useAppState();
  useEffect(() => {
    dispatch({ type: "upsert_task", task: value });
  }, [dispatch, value]);
  return null;
}

describe("AppLayout task status", () => {
  it("shows interrupted task state and disables task controls", async () => {
    render(
      <AppStateProvider>
        <SeedTask value={task()} />
        <AppLayout>
          <div>页面内容</div>
        </AppLayout>
      </AppStateProvider>
    );

    expect(await screen.findByText("已中断")).toBeInTheDocument();
    expect(screen.getByText(/后端重启时任务仍未结束/)).toBeInTheDocument();
    expect(screen.getByLabelText("恢复")).toBeDisabled();
    expect(screen.getByLabelText("暂停")).toBeDisabled();
    expect(screen.getByLabelText("取消")).toBeDisabled();
  });

  it("keeps persisted cancelled task display distinct", async () => {
    render(
      <AppStateProvider>
        <SeedTask value={task({ status: "cancelled", error: null, progress_text: "" })} />
        <AppLayout>
          <div>页面内容</div>
        </AppLayout>
      </AppStateProvider>
    );

    expect(await screen.findByText("已取消")).toBeInTheDocument();
    expect(screen.getByText("任务已取消")).toBeInTheDocument();
  });
});
