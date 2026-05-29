import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { beforeEach, describe, expect, it } from "vitest";
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

function event(message: string, overrides: Partial<TaskRecord["events"][number]> = {}): TaskRecord["events"][number] {
  return {
    task_id: "task-1",
    event_type: "state",
    message,
    source_id: "global",
    event_id: 1,
    status: "success",
    progress_text: null,
    data: {},
    timestamp: 1,
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

function RestoreTasks({ items }: { items: TaskRecord[] }) {
  const { dispatch } = useAppState();
  useEffect(() => {
    dispatch({ type: "restore_tasks", items });
  }, [dispatch, items]);
  return null;
}

describe("AppLayout task status", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

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
    expect(screen.getAllByText(/后端重启时任务仍未结束/).length).toBeGreaterThan(0);
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

  it("does not show restored terminal task summaries in the top status area", async () => {
    const restoredTasks = [
      task({
        status: "success",
        progress_text: "",
        result_summary: "generated 2 files",
        error: null,
        events: [event("Task completed")]
      })
    ];

    render(
      <AppStateProvider>
        <RestoreTasks items={restoredTasks} />
        <AppLayout>
          <div>页面内容</div>
        </AppLayout>
      </AppStateProvider>
    );

    expect(await screen.findByText("任务待命")).toBeInTheDocument();
    expect(screen.getByText("空闲")).toBeInTheDocument();
    expect(screen.queryByText("generated 2 files")).not.toBeInTheDocument();
    expect(screen.queryByText("已完成")).not.toBeInTheDocument();
    expect(screen.getByText("暂无日志")).toBeInTheDocument();
    expect(screen.queryByText("Task completed")).not.toBeInTheDocument();
  });

  it("shows restored active tasks as current work", async () => {
    const restoredTasks = [
      task({
        status: "running",
        progress_text: "正在分割章节",
        result_summary: null,
        error: null,
        finished_at: null,
        events: [
          event("Task started", {
            status: "running"
          })
        ]
      })
    ];

    render(
      <AppStateProvider>
        <RestoreTasks items={restoredTasks} />
        <AppLayout>
          <div>页面内容</div>
        </AppLayout>
      </AppStateProvider>
    );

    expect(await screen.findByText("运行中")).toBeInTheDocument();
    expect(screen.getByText("正在分割章节")).toBeInTheDocument();
    expect(screen.getByText("Task started")).toBeInTheDocument();
    expect(screen.getByLabelText("暂停")).toBeEnabled();
    expect(screen.getByLabelText("取消")).toBeEnabled();
  });

  it("counts only active tasks in the sidebar index", async () => {
    const restoredTasks = [
      task({
        task_id: "task-done",
        status: "success",
        progress_text: "",
        result_summary: "generated 2 files",
        error: null,
        events: [event("Done", { task_id: "task-done", status: "success" })]
      }),
      task({
        task_id: "task-failed",
        status: "failed",
        progress_text: "",
        error: "failed",
        finished_at: 3,
        events: [event("Failed", { task_id: "task-failed", status: "failed" })]
      }),
      task({
        task_id: "task-running",
        status: "running",
        progress_text: "正在分割章节",
        error: null,
        finished_at: null,
        events: [event("Task started", { task_id: "task-running", status: "running" })]
      }),
      task({
        task_id: "task-paused",
        status: "paused",
        progress_text: "等待恢复",
        error: null,
        finished_at: null,
        events: [event("Task paused", { task_id: "task-paused", status: "paused" })]
      })
    ];

    render(
      <AppStateProvider>
        <RestoreTasks items={restoredTasks} />
        <AppLayout>
          <div>页面内容</div>
        </AppLayout>
      </AppStateProvider>
    );

    const activeTaskStat = await screen.findByText("活动任务");

    expect(screen.queryByText("会话任务")).not.toBeInTheDocument();
    expect(within(activeTaskStat.parentElement as HTMLElement).getByText("2")).toBeInTheDocument();
  });

  it("keeps task logs compact until expanded or pinned for debugging", async () => {
    const user = userEvent.setup();
    const restoredTasks = [
      task({
        status: "running",
        progress_text: "正在分割章节",
        result_summary: null,
        error: null,
        finished_at: null,
        events: [
          event("Task started", {
            status: "running"
          })
        ]
      })
    ];

    render(
      <AppStateProvider>
        <RestoreTasks items={restoredTasks} />
        <AppLayout>
          <div>页面内容</div>
        </AppLayout>
      </AppStateProvider>
    );

    expect(await screen.findByText("Task started")).toBeInTheDocument();
    expect(screen.queryByRole("log")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("展开日志"));

    expect(screen.getByRole("log")).toBeInTheDocument();
    expect(screen.getByText("展开视图")).toBeInTheDocument();

    await user.click(screen.getByLabelText("钉住日志"));

    expect(screen.getByText("调试模式")).toBeInTheDocument();
    expect(window.localStorage.getItem("studio.logPanelPinned")).toBe("true");

    await user.click(screen.getByLabelText("退出调试模式"));

    await waitFor(() => expect(screen.queryByRole("log")).not.toBeInTheDocument());
  });
});
