import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { TaskRecord } from "../api/types";
import { SummaryPartialNotice } from "./SummaryPartialNotice";

function task(overrides: Partial<TaskRecord> = {}): TaskRecord {
  return {
    task_id: "task-1",
    task_type: "article_summary",
    status: "partial_failed",
    progress_text: "",
    created_at: 1,
    updated_at: 2,
    finished_at: 3,
    result_summary: "partial_failed",
    error: null,
    warnings: [],
    result_data: {},
    params_summary: {},
    events: [],
    ...overrides
  };
}

describe("SummaryPartialNotice", () => {
  it("shows article warnings, failed sections, and retained output path", () => {
    render(
      <SummaryPartialNotice
        kind="article"
        task={task({
          warnings: ["最终总结可能不完整"],
          result_data: {
            final_output_path: "out/final.txt",
            failed_sections: [{ filename: "2.txt", error: "section boom" }]
          }
        })}
      />
    );

    expect(screen.getByText("文章总结部分结果")).toBeInTheDocument();
    expect(screen.getByText("最终总结可能不完整")).toBeInTheDocument();
    expect(screen.getByText("2.txt：section boom")).toBeInTheDocument();
    expect(screen.getByText("可用结果：out/final.txt")).toBeInTheDocument();
  });

  it("shows custom fallback warning and retained output when details are missing", () => {
    render(
      <SummaryPartialNotice
        kind="custom"
        task={task({
          task_type: "custom_summary",
          result_summary: "partial output",
          result_data: { output_text: "完整自定义总结" }
        })}
      />
    );

    expect(screen.getByText("自定义总结部分结果")).toBeInTheDocument();
    expect(screen.getByText(/自定义总结已保留可用结果/)).toBeInTheDocument();
    expect(screen.getByText("部分输入失败，未返回详细列表。")).toBeInTheDocument();
    expect(screen.getByText("可用结果：完整自定义总结")).toBeInTheDocument();
  });

  it("does not render for non-partial tasks", () => {
    const { container } = render(
      <SummaryPartialNotice kind="article" task={task({ status: "success" })} />
    );

    expect(container).toBeEmptyDOMElement();
  });
});
