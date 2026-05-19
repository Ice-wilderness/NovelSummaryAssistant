import { useEffect, useMemo, useRef, useState } from "react";
import type { TaskEvent } from "../../api/types";
import { useAppState } from "../../state/AppState";

function formatTime(timestamp: number) {
  return new Date(timestamp * 1000).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function eventTone(event: TaskEvent) {
  const status = String(event.status ?? "").toLowerCase();
  if (event.event_type === "error" || status.includes("fail")) {
    return "danger";
  }
  if (status.includes("success") || status.includes("ok")) {
    return "success";
  }
  if (status.includes("warn")) {
    return "warning";
  }
  return "default";
}

export function LogPanel() {
  const { state } = useAppState();
  const sourceIds = useMemo(
    () => Object.keys(state.apiEvents).filter((sourceId) => sourceId !== "global"),
    [state.apiEvents]
  );
  const [activeSource, setActiveSource] = useState("global");
  const logStreamRef = useRef<HTMLDivElement | null>(null);
  const events =
    activeSource === "global" ? state.events : state.apiEvents[activeSource] ?? [];

  useEffect(() => {
    const stream = logStreamRef.current;
    if (stream) {
      stream.scrollTop = stream.scrollHeight;
    }
  }, [activeSource, events.length]);

  return (
    <aside className="log-panel">
      <div className="log-panel__header">
        <h2>日志</h2>
        <div className="log-tabs" role="tablist">
          <button
            aria-selected={activeSource === "global"}
            className="log-tab"
            onClick={() => setActiveSource("global")}
            role="tab"
            type="button"
          >
            全局
          </button>
          {sourceIds.map((sourceId) => (
            <button
              aria-selected={activeSource === sourceId}
              className="log-tab"
              key={sourceId}
              onClick={() => setActiveSource(sourceId)}
              role="tab"
              title={sourceId}
              type="button"
            >
              {sourceId}
            </button>
          ))}
        </div>
      </div>
      <div className="log-stream" ref={logStreamRef} role="log">
        {events.length === 0 ? (
          <span className="empty-state">暂无日志</span>
        ) : (
          events.map((event) => (
            <article
              className={`log-line log-line--${eventTone(event)}`}
              key={`${event.timestamp}-${event.source_id}-${event.message}`}
            >
              <time>{formatTime(event.timestamp)}</time>
              <strong>{event.source_id}</strong>
              <span>{event.message || event.progress_text || event.event_type}</span>
            </article>
          ))
        )}
      </div>
    </aside>
  );
}
