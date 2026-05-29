import type { ReactNode } from "react";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import type { TaskEvent, TaskRecord } from "../api/types";
import { AppStateProvider, useAppState } from "../state/AppState";
import { useTaskActions } from "./useTaskActions";

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

  emitMessage(event: Partial<TaskEvent>) {
    this.onmessage?.({
      data: JSON.stringify({
        task_id: "task-1",
        event_type: "progress",
        message: "",
        source_id: "global",
        status: "running",
        progress_text: null,
        data: {},
        timestamp: 1,
        ...event
      })
    } as MessageEvent);
  }

  emit(type: string, data: unknown) {
    const event = { data: JSON.stringify(data) } as MessageEvent;
    (this.listeners.get(type) ?? []).forEach((listener) => listener(event));
  }

  fail() {
    this.onerror?.(new Event("error"));
  }
}

function wrapper({ children }: { children: ReactNode }) {
  return <AppStateProvider>{children}</AppStateProvider>;
}

function task(overrides: Partial<TaskRecord> = {}): TaskRecord {
  return {
    task_id: "task-1",
    task_type: "model_fetch",
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
    events: [],
    ...overrides
  };
}

describe("useTaskActions", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("EventSource", FakeEventSource);
    vi.spyOn(apiClient, "getTask").mockResolvedValue(task());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    FakeEventSource.instances = [];
  });

  it("deduplicates replayed events and reconnects with the latest cursor", async () => {
    const { result } = renderHook(
      () => ({
        actions: useTaskActions(),
        app: useAppState()
      }),
      { wrapper }
    );

    act(() => {
      result.current.actions.watchTask(task());
    });

    const firstSource = FakeEventSource.instances[0];
    expect(firstSource.url).toBe("/api/tasks/task-1/events");

    act(() => {
      firstSource.emitMessage({ event_id: 1, message: "one" });
      firstSource.emitMessage({ event_id: 1, message: "one duplicate" });
      firstSource.emit("heartbeat", { task_id: "task-1" });
    });

    expect(result.current.app.state.events).toHaveLength(1);
    expect(result.current.app.state.events[0].message).toBe("one");

    await act(async () => {
      firstSource.fail();
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(250);
    });

    expect(apiClient.getTask).toHaveBeenCalledWith("task-1");
    const secondSource = FakeEventSource.instances[1];
    expect(secondSource.url).toBe("/api/tasks/task-1/events?last_event_id=1");
  });

  it("refreshes task status on replay gaps and terminal events", async () => {
    const terminalTask = task({ task_id: "task-2", status: "success", finished_at: 2 });
    vi.mocked(apiClient.getTask).mockResolvedValue(terminalTask);
    const onTaskTerminal = vi.fn();
    const { result } = renderHook(
      () => ({
        actions: useTaskActions({ onTaskTerminal }),
        app: useAppState()
      }),
      { wrapper }
    );

    act(() => {
      result.current.actions.watchTask(task({ task_id: "task-2" }));
    });

    const eventSource = FakeEventSource.instances[0];

    await act(async () => {
      eventSource.emit("replay_gap", {
        task_id: "task-2",
        event_type: "replay_gap",
        message: "gap",
        source_id: "global",
        status: "running",
        progress_text: null,
        data: { replay_gap: true },
        timestamp: 1
      });
      await Promise.resolve();
    });

    expect(apiClient.getTask).toHaveBeenCalledWith("task-2");
    expect(result.current.app.state.events).toHaveLength(0);

    await act(async () => {
      eventSource.emitMessage({
        task_id: "task-2",
        event_id: 2,
        status: "success",
        message: "done"
      });
      await Promise.resolve();
    });

    expect(result.current.app.state.events).toHaveLength(1);
    expect(onTaskTerminal).toHaveBeenCalledWith(terminalTask);
    expect(eventSource.close).toHaveBeenCalled();
  });

  it("clears replay cache after terminal refresh", async () => {
    const terminalTask = task({ task_id: "task-3", status: "success", finished_at: 3 });
    vi.mocked(apiClient.getTask).mockResolvedValue(terminalTask);
    const { result } = renderHook(
      () => ({
        actions: useTaskActions(),
        app: useAppState()
      }),
      { wrapper }
    );

    act(() => {
      result.current.actions.watchTask(task({ task_id: "task-3" }));
    });
    const firstSource = FakeEventSource.instances[0];

    await act(async () => {
      firstSource.emitMessage({ task_id: "task-3", event_id: 7, message: "before terminal" });
      firstSource.emitMessage({
        task_id: "task-3",
        event_id: 8,
        status: "success",
        message: "done"
      });
      await Promise.resolve();
    });

    expect(firstSource.close).toHaveBeenCalled();

    vi.mocked(apiClient.getTask).mockResolvedValue(task({ task_id: "task-3" }));
    act(() => {
      result.current.actions.watchTask(task({ task_id: "task-3" }));
    });

    const secondSource = FakeEventSource.instances[1];
    expect(secondSource.url).toBe("/api/tasks/task-3/events");

    act(() => {
      secondSource.emitMessage({ task_id: "task-3", event_id: 7, message: "accepted again" });
    });

    expect(result.current.app.state.events.map((event) => event.message)).toContain("accepted again");
  });

  it("preserves other active task replay caches after terminal cleanup", async () => {
    vi.mocked(apiClient.getTask).mockImplementation(async (taskId: string) =>
      task({
        task_id: taskId,
        status: taskId === "task-4" ? "success" : "running",
        finished_at: taskId === "task-4" ? 4 : null
      })
    );
    const { result } = renderHook(
      () => ({
        actions: useTaskActions(),
        app: useAppState()
      }),
      { wrapper }
    );

    act(() => {
      result.current.actions.watchTask(task({ task_id: "task-4" }));
      result.current.actions.watchTask(task({ task_id: "task-5" }));
    });
    const terminalSource = FakeEventSource.instances[0];
    const activeSource = FakeEventSource.instances[1];

    await act(async () => {
      activeSource.emitMessage({ task_id: "task-5", event_id: 3, message: "active cursor" });
      terminalSource.emitMessage({
        task_id: "task-4",
        event_id: 1,
        status: "success",
        message: "terminal"
      });
      await Promise.resolve();
      activeSource.fail();
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(250);
    });

    const reconnectedActiveSource = FakeEventSource.instances[2];
    expect(reconnectedActiveSource.url).toBe("/api/tasks/task-5/events?last_event_id=3");
  });
});
