import { ChevronDown, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiDisplayName } from "../../api/display";
import type { TaskEvent } from "../../api/types";
import { useAppState } from "../../state/AppState";

const COLLAPSE_THRESHOLD = 220;

function formatTime(timestamp: number) {
  return new Date(timestamp * 1000).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function eventTone(event: TaskEvent) {
  const status = String(event.status ?? "").toLowerCase();
  const message = `${event.event_type} ${event.message} ${event.progress_text ?? ""}`.toLowerCase();
  if (
    event.event_type === "error" ||
    status.includes("fail") ||
    message.includes("error") ||
    message.includes("failed") ||
    message.includes("失败") ||
    message.includes("错误")
  ) {
    return "danger";
  }
  if (
    status.includes("success") ||
    status.includes("ok") ||
    message.includes("success") ||
    message.includes("完成")
  ) {
    return "success";
  }
  if (
    status.includes("warn") ||
    message.includes("warn") ||
    message.includes("警告") ||
    message.includes("重试")
  ) {
    return "warning";
  }
  return "default";
}

function logText(event: TaskEvent) {
  return event.message || event.progress_text || event.event_type;
}

function eventLabel(event: TaskEvent) {
  if (event.event_type === "state") {
    return "状态";
  }
  if (event.event_type === "progress") {
    return "进度";
  }
  if (event.event_type === "error") {
    return "错误";
  }
  if (event.event_type === "log") {
    return "日志";
  }
  return event.event_type;
}

export function LogPanel() {
  const { state } = useAppState();
  const sourceLabels = useMemo(() => {
    const labels = new Map<string, string>();
    state.apiConfigs.forEach((config) => labels.set(config.id, apiDisplayName(config)));
    if (state.apiConfigs.length === 1) {
      labels.set("UnknownAPI", apiDisplayName(state.apiConfigs[0]));
    }
    labels.set("global", "全局");
    return labels;
  }, [state.apiConfigs]);
  const sourceIds = useMemo(
    () => Object.keys(state.apiEvents).filter((sourceId) => sourceId !== "global"),
    [state.apiEvents]
  );
  const [activeSource, setActiveSource] = useState("global");
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(() => new Set());
  const logStreamRef = useRef<HTMLDivElement | null>(null);
  const events =
    activeSource === "global" ? state.events : state.apiEvents[activeSource] ?? [];

  useEffect(() => {
    const stream = logStreamRef.current;
    if (stream) {
      stream.scrollTop = stream.scrollHeight;
    }
  }, [activeSource, events.length]);

  const toggleLog = (key: string) => {
    setExpandedLogs((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  return (
    <aside className="log-panel">
      <div className="log-panel__header">
        <div className="log-panel__title">
          <h2>日志</h2>
          <span>{events.length} 条</span>
        </div>
        <p className="log-panel__hint">
          全局显示所有任务事件，API 标签只看对应来源；长日志可展开查看完整内容。
        </p>
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
              title={sourceLabels.get(sourceId) ?? sourceId}
              type="button"
            >
              {sourceLabels.get(sourceId) ?? sourceId}
            </button>
          ))}
        </div>
      </div>
      <div className="log-stream" ref={logStreamRef} role="log">
        {events.length === 0 ? (
          <span className="empty-state">暂无日志</span>
        ) : (
          events.map((event, index) => {
            const key = `${event.timestamp}-${event.source_id}-${index}`;
            const message = logText(event);
            const canExpand = message.length > COLLAPSE_THRESHOLD || message.includes("\n");
            const isExpanded = expandedLogs.has(key);
            const tone = eventTone(event);

            return (
              <article
                className={`log-entry log-entry--${tone} ${isExpanded ? "log-entry--expanded" : ""}`}
                key={key}
              >
                <div className="log-entry__meta">
                  <span className="log-entry__tone" aria-hidden="true" />
                  <time>{formatTime(event.timestamp)}</time>
                  <strong title={sourceLabels.get(event.source_id) ?? event.source_id}>
                    {sourceLabels.get(event.source_id) ?? event.source_id}
                  </strong>
                  <span className="log-entry__type">{eventLabel(event)}</span>
                </div>
                <p className={`log-entry__message ${canExpand && !isExpanded ? "log-entry__message--collapsed" : ""}`}>
                  {message}
                </p>
                {canExpand ? (
                  <button
                    className="log-entry__toggle"
                    onClick={() => toggleLog(key)}
                    type="button"
                  >
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    <span>{isExpanded ? "收起" : "展开"}</span>
                  </button>
                ) : null}
              </article>
            );
          })
        )}
      </div>
    </aside>
  );
}
