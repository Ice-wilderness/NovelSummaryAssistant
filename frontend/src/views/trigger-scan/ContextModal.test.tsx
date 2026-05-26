import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ScanFinding } from "../../api/types";
import { ContextModal, type ContextState } from "./ContextModal";

function finding(): ScanFinding {
  return {
    finding_id: "finding-1",
    rule_id: "rule-1",
    rule_name: "规则一",
    chapter_file: "chapters/chapter-001.txt",
    chapter_title: "第一章",
    paragraph_ids: ["P1", "P2"],
    severity: 4,
    confidence: 0.91,
    is_main_plot: true,
    review_status: "unreviewed",
    user_note: "",
    spoiler_levels: {
      low: {
        description: "低剧透描述",
        evidence_quote: "",
        skip_advice: ""
      },
      standard: {
        description: "标准描述",
        evidence_quote: "",
        skip_advice: ""
      },
      detailed: {
        description: "详细描述",
        evidence_quote: "证据句",
        skip_advice: "跳过建议"
      }
    }
  };
}

function contextState(overrides: Partial<ContextState> = {}): ContextState {
  return {
    error: "",
    finding: finding(),
    isLoading: false,
    response: {
      ok: true,
      missing_paragraph_ids: ["P3"],
      paragraphs: [
        {
          id: "P1",
          line_number: 1,
          matched: true,
          text: "触发段落"
        },
        {
          id: "P2",
          line_number: 2,
          matched: false,
          text: "相邻段落"
        }
      ]
    },
    ...overrides
  };
}

describe("ContextModal", () => {
  it("renders matched paragraphs and missing paragraph hints", () => {
    render(<ContextModal contextState={contextState()} onClose={vi.fn()} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("触发段落")).toBeInTheDocument();
    expect(screen.getByText("触发段落").closest(".context-paragraph")).toHaveClass(
      "context-paragraph--matched"
    );
    expect(screen.getByText("缺失段落：P3")).toBeInTheDocument();
  });

  it("delegates close actions", () => {
    const onClose = vi.fn();
    render(<ContextModal contextState={contextState()} onClose={onClose} />);

    fireEvent.click(screen.getByRole("button"));

    expect(onClose).toHaveBeenCalled();
  });
});
