import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import { AppStateProvider } from "../state/AppState";
import { SplitterPage } from "./SplitterPage";

describe("SplitterPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows preview safety errors from the API", async () => {
    vi.spyOn(apiClient, "pickDirectory").mockResolvedValue("C:/out");
    vi.spyOn(apiClient, "previewSplit").mockRejectedValue(new Error("正则表达式包含高风险"));

    render(
      <AppStateProvider>
        <SplitterPage />
      </AppStateProvider>
    );

    await chooseSourceAndOutput();

    fireEvent.click(screen.getByRole("button", { name: /预览分割/ }));

    await waitFor(() => {
      expect(screen.getByText("正则表达式包含高风险")).toBeInTheDocument();
    });
  });

  it("shows direct split failures without clearing the selected source", async () => {
    vi.spyOn(apiClient, "pickDirectory").mockResolvedValue("C:/out");
    vi.spyOn(apiClient, "directSplit").mockRejectedValue(new Error("未匹配到任何章节"));

    render(
      <AppStateProvider>
        <SplitterPage />
      </AppStateProvider>
    );

    await chooseSourceAndOutput();
    fireEvent.click(screen.getByRole("button", { name: /开始/ }));

    await waitFor(() => {
      expect(screen.getByText("分割失败：未匹配到任何章节")).toBeInTheDocument();
    });
    expect(screen.getByText("source.txt")).toBeInTheDocument();
  });

  it("disables start while splitting and clears source after success", async () => {
    let resolveSplit: (value: { success: boolean; file_count: number; output_directory: string }) => void = () => undefined;
    vi.spyOn(apiClient, "pickDirectory").mockResolvedValue("C:/out");
    vi.spyOn(apiClient, "directSplit").mockReturnValue(
      new Promise((resolve) => {
        resolveSplit = resolve;
      })
    );

    render(
      <AppStateProvider>
        <SplitterPage />
      </AppStateProvider>
    );

    await chooseSourceAndOutput();
    const startButton = screen.getByRole("button", { name: /^开始$/ });
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(startButton).toBeDisabled();
    });

    resolveSplit({ success: true, file_count: 2, output_directory: "C:/out" });

    await waitFor(() => {
      expect(screen.getByText("分割完成，共生成 2 个章节文件")).toBeInTheDocument();
    });
    expect(screen.queryByText("source.txt")).not.toBeInTheDocument();
  });
});

async function chooseSourceAndOutput() {
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

  fireEvent.click(screen.getByRole("button", { name: /浏览/ }));
  await waitFor(() => {
    expect(screen.getByDisplayValue("C:/out")).toBeInTheDocument();
  });
  await new Promise((resolve) => setTimeout(resolve, 0));
}
