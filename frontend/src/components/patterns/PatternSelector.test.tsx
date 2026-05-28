import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../api/client";
import { PatternSelector } from "./PatternSelector";

describe("PatternSelector", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows chapter pattern recovery warnings near the selector", async () => {
    vi.spyOn(apiClient, "listPatternResponse").mockResolvedValue({
      items: [],
      warnings: [
        {
          domain: "chapter_patterns",
          message: "章节模式配置文件损坏，已恢复为默认配置",
          path: "chapter_patterns.json",
          backup_path: "chapter_patterns.json.bak",
          backup_failed: false
        }
      ]
    });

    render(<PatternSelector configId="" onChange={vi.fn()} />);

    expect(await screen.findByText("章节模式配置文件损坏，已恢复为默认配置")).toBeInTheDocument();
  });
});
