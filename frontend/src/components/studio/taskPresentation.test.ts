import { describe, expect, it } from "vitest";
import type { TaskRecord } from "../../api/types";
import { taskHeadline, taskTerminalMessage } from "./taskPresentation";

function task(overrides: Partial<TaskRecord> = {}): TaskRecord {
  return {
    task_id: "task-1",
    task_type: "novel_summary",
    status: "success",
    progress_text: "",
    created_at: 1,
    updated_at: 2,
    finished_at: 3,
    result_summary: null,
    error: null,
    warnings: [],
    result_data: {},
    params_summary: {},
    events: [],
    ...overrides
  };
}

describe("taskPresentation", () => {
  it("replaces raw terminal status strings with readable task summaries", () => {
    const value = task({
      progress_text: "success",
      result_summary: "success"
    });

    expect(taskHeadline(value)).toBe("小说总结已完成");
    expect(taskTerminalMessage(value)).toBe("小说总结已完成");
  });

  it("keeps meaningful terminal messages when available", () => {
    const value = task({
      result_summary: "exports/novel/final.md"
    });

    expect(taskHeadline(value)).toBe("exports/novel/final.md");
    expect(taskTerminalMessage(value)).toBe("exports/novel/final.md");
  });

  it("adds task context for raw failure errors", () => {
    const value = task({
      task_type: "chapter_split",
      status: "failed",
      error: "failed"
    });

    expect(taskHeadline(value)).toBe("章节分割失败");
    expect(taskTerminalMessage(value)).toBe("章节分割失败");
  });
});
