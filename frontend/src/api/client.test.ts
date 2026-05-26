import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiClient } from "./client";

function mockFetch(response: Response) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("apiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses successful JSON responses", async () => {
    mockFetch(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    await expect(apiClient.health()).resolves.toEqual({ status: "ok" });
  });

  it("preserves backend detail from failed JSON responses", async () => {
    mockFetch(
      new Response(JSON.stringify({ detail: "配置无效" }), {
        status: 400,
        statusText: "Bad Request",
        headers: { "Content-Type": "application/json" }
      })
    );

    await expect(apiClient.health()).rejects.toMatchObject<ApiError>({
      name: "ApiError",
      status: 400,
      detail: "配置无效",
      message: "配置无效"
    });
  });

  it("turns failed non-JSON responses into readable ApiError objects", async () => {
    mockFetch(
      new Response("<html>upstream failed</html>", {
        status: 502,
        statusText: "Bad Gateway",
        headers: { "Content-Type": "text/html" }
      })
    );

    try {
      await apiClient.health();
      throw new Error("expected health request to fail");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({
        status: 502,
        detail: "Bad Gateway: <html>upstream failed</html>"
      });
    }
  });

  it("uses status text for empty failed responses", async () => {
    mockFetch(
      new Response("", {
        status: 503,
        statusText: "Service Unavailable"
      })
    );

    await expect(apiClient.health()).rejects.toMatchObject({
      status: 503,
      detail: "Service Unavailable"
    });
  });

  it("posts splitter tasks through the shared API client", async () => {
    const fetchMock = mockFetch(
      new Response(
        JSON.stringify({
          task_id: "task-1",
          task_type: "chapter_split",
          status: "running",
          progress_text: "",
          created_at: 1,
          updated_at: 1,
          finished_at: null,
          result_summary: null,
          error: null,
          warnings: [],
          result_data: {},
          params_summary: {},
          events: []
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    await apiClient.startSplitter({
      source_txt_file_path: "",
      output_directory_path: "",
      mode: "default",
      custom_pattern: "",
      title_list: [],
      handle_volumes: true,
      context: "novel_summary",
      file_content: "正文",
      project_name: "Demo",
      project_slug: "demo",
      uploaded_file_ids: []
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/tasks/splitter",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          source_txt_file_path: "",
          output_directory_path: "",
          mode: "default",
          custom_pattern: "",
          title_list: [],
          handle_volumes: true,
          context: "novel_summary",
          file_content: "正文",
          project_name: "Demo",
          project_slug: "demo",
          uploaded_file_ids: []
        })
      })
    );
  });
});
