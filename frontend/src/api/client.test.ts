import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiClient, subscribeTaskEvents } from "./client";

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  listeners = new Map<string, Array<(event: MessageEvent) => void>>();
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener as (event: MessageEvent) => void);
    this.listeners.set(type, listeners);
  }

  emit(type: string, data: unknown) {
    const event = { data: JSON.stringify(data) } as MessageEvent;
    (this.listeners.get(type) ?? []).forEach((listener) => listener(event));
  }
}

function mockFetch(response: Response) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("apiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    FakeEventSource.instances = [];
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

    await expect(apiClient.health()).rejects.toMatchObject({
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
      source_txt_file_path: "source.txt",
      output_directory_path: "out",
      mode: "default",
      custom_pattern: "",
      title_list: [],
      handle_volumes: true,
      context: "chapter_split"
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/tasks/splitter",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          source_txt_file_path: "source.txt",
          output_directory_path: "out",
          mode: "default",
          custom_pattern: "",
          title_list: [],
          handle_volumes: true,
          context: "chapter_split"
        })
      })
    );
  });

  it("posts source split-and-ingest requests and returns the updated project", async () => {
    const project = {
      project_name: "Demo",
      project_slug: "demo",
      workflow_type: "novel_summary",
      uploads: [{ id: "split-1", original_name: "第001章.txt" }]
    };
    const fetchMock = mockFetch(
      new Response(JSON.stringify(project), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    await expect(
      apiClient.splitAndIngestSource({
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
    ).resolves.toEqual(project);

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

  it("subscribes to task events with replay cursor and heartbeat handlers", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    const onEvent = vi.fn();
    const onHeartbeat = vi.fn();
    const onReplayGap = vi.fn();

    subscribeTaskEvents(
      "task-1",
      {
        onEvent,
        onHeartbeat,
        onReplayGap
      },
      { lastEventId: 3 }
    );

    const eventSource = FakeEventSource.instances[0];
    expect(eventSource.url).toBe("/api/tasks/task-1/events?last_event_id=3");

    eventSource.onmessage?.({
      data: JSON.stringify({ task_id: "task-1", event_type: "progress", event_id: 4 })
    } as MessageEvent);
    eventSource.emit("heartbeat", { task_id: "task-1" });
    eventSource.emit("replay_gap", {
      task_id: "task-1",
      event_type: "replay_gap",
      data: { replay_gap: true }
    });

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({ task_id: "task-1", event_id: 4 })
    );
    expect(onHeartbeat).toHaveBeenCalledWith("task-1");
    expect(onReplayGap).toHaveBeenCalledWith(
      expect.objectContaining({ event_type: "replay_gap" })
    );
  });
});
