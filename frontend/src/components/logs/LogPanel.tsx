import {
  Activity,
  Bug,
  ChevronDown,
  ChevronRight,
  Maximize2,
  Minimize2,
  Pin,
  PinOff,
  Trash2,
  TriangleAlert
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiDisplayName } from "../../api/display";
import type { TaskEvent, TaskRecord } from "../../api/types";
import { useTaskAvailability } from "../../hooks/useTaskAvailability";
import { useAppState } from "../../state/AppState";
import { IconButton } from "../common/IconButton";

const COLLAPSE_THRESHOLD = 220;
const LOG_PANEL_PINNED_KEY = "studio.logPanelPinned";
const BUSY_STATUSES = new Set(["pending", "running", "paused", "canceling"]);

type EventTone = "danger" | "success" | "warning" | "default";
type FeedbackTone = "active" | "danger" | "idle" | "success" | "warning";

function formatTime(timestamp: number) {
  return new Date(timestamp * 1000).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function eventTone(event: TaskEvent): EventTone {
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

function feedbackTone(
  latestTask: TaskRecord | null,
  latestEvent: TaskEvent | undefined,
  isTaskBusy: boolean
): FeedbackTone {
  const latestEventTone = latestEvent ? eventTone(latestEvent) : "default";
  if (
    latestEventTone === "danger" ||
    latestTask?.status === "failed" ||
    latestTask?.status === "interrupted"
  ) {
    return "danger";
  }
  if (
    latestEventTone === "warning" ||
    latestTask?.status === "paused" ||
    latestTask?.status === "cancelled" ||
    latestTask?.status === "partial_failed" ||
    Boolean(latestTask?.warnings.length)
  ) {
    return "warning";
  }
  if (isTaskBusy || BUSY_STATUSES.has(latestTask?.status ?? "")) {
    return "active";
  }
  if (latestTask?.status === "success" || latestEventTone === "success") {
    return "success";
  }
  return "idle";
}

function feedbackLabel(tone: FeedbackTone) {
  if (tone === "active") {
    return "实时运行";
  }
  if (tone === "danger") {
    return "需要查看";
  }
  if (tone === "warning") {
    return "需要留意";
  }
  if (tone === "success") {
    return "已完成";
  }
  return "工作模式";
}

function logText(event: TaskEvent) {
  return event.message || event.progress_text || event.event_type;
}

function taskFallbackMessage(task: TaskRecord | null) {
  if (!task) {
    return "暂无日志";
  }
  return task.error || task.warnings[0] || task.progress_text || "暂无日志";
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
  const { state, dispatch } = useAppState();
  const { isTaskBusy, latestTask } = useTaskAvailability();
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
  const [isExpanded, setIsExpanded] = useState(false);
  const [isPinned, setIsPinned] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }
    try {
      return window.localStorage.getItem(LOG_PANEL_PINNED_KEY) === "true";
    } catch {
      return false;
    }
  });
  const logStreamRef = useRef<HTMLDivElement | null>(null);
  const events =
    activeSource === "global" ? state.events : state.apiEvents[activeSource] ?? [];
  const totalEvents = state.events.length;
  const hasEvents = totalEvents > 0;
  const latestEvent = hasEvents ? state.events[totalEvents - 1] : undefined;
  const tone = feedbackTone(latestTask, latestEvent, isTaskBusy);
  const latestMessage = latestEvent ? logText(latestEvent) : taskFallbackMessage(latestTask);
  const shouldShowDock =
    hasEvents ||
    isTaskBusy ||
    latestTask?.status === "failed" ||
    latestTask?.status === "interrupted" ||
    latestTask?.status === "partial_failed" ||
    latestTask?.status === "cancelled";
  const isPanelOpen = isExpanded || isPinned;
  const panelModeLabel = isPinned ? "调试模式" : "展开视图";

  useEffect(() => {
    if (activeSource !== "global" && !sourceIds.includes(activeSource)) {
      setActiveSource("global");
    }
  }, [activeSource, sourceIds]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      window.localStorage.setItem(LOG_PANEL_PINNED_KEY, String(isPinned));
    } catch {
      // localStorage can be unavailable in private or embedded environments.
    }
  }, [isPinned]);

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
  const clearLogs = () => {
    setActiveSource("global");
    setExpandedLogs(new Set());
    if (!isPinned) {
      setIsExpanded(false);
    }
    dispatch({ type: "clear_events" });
  };
  const openPanel = () => setIsExpanded(true);
  const closePanel = () => {
    setIsExpanded(false);
    if (isPinned) {
      setIsPinned(false);
    }
  };
  const toggleDebugMode = () => {
    setIsPinned((current) => !current);
    setIsExpanded(false);
  };

  const renderTicker = (variant: "capsule" | "dock") => (
    <motion.section
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={`studio-log-${variant} studio-log-${variant}--${tone}`}
      initial={{ opacity: 0, y: 12, scale: variant === "capsule" ? 0.98 : 1 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      aria-label="实时反馈"
    >
      <div className={`studio-log-${variant}__signal`} aria-hidden="true">
        {tone === "danger" || tone === "warning" ? (
          <TriangleAlert size={16} />
        ) : (
          <Activity size={16} />
        )}
      </div>
      <div className={`studio-log-${variant}__copy`}>
        <span>{feedbackLabel(tone)}</span>
        <strong>实时反馈</strong>
        <p>{latestMessage}</p>
      </div>
      <div className={`studio-log-${variant}__actions`}>
        <span>{totalEvents} 条</span>
        <IconButton
          className="studio-log-action"
          label="展开日志"
          onClick={openPanel}
        >
          <Maximize2 size={15} />
        </IconButton>
        <IconButton
          className="studio-log-action studio-log-action--debug"
          label={isPinned ? "关闭调试模式" : "启用调试模式"}
          onClick={toggleDebugMode}
        >
          <Bug size={15} />
        </IconButton>
      </div>
      {variant === "dock" && tone === "active" ? (
        <span className="studio-log-dock__sweep" aria-hidden="true" />
      ) : null}
    </motion.section>
  );

  const renderFullPanel = () => (
    <motion.aside
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={`log-panel studio-log-panel ${isPinned ? "studio-log-panel--pinned" : "studio-log-panel--drawer"}`}
      exit={{ opacity: 0, y: 18, scale: 0.985 }}
      initial={{ opacity: 0, y: 22, scale: 0.985 }}
      transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
      aria-label="实时反馈"
    >
      <div className="log-panel__header">
        <div className="log-panel__title">
          <div className="log-panel__heading">
            <h2>实时反馈</h2>
            <span className="log-panel__mode">{panelModeLabel}</span>
          </div>
          <div className="log-panel__actions">
            <span>{events.length} 条</span>
            <IconButton
              className="log-panel__clear"
              disabled={!hasEvents}
              label="清除日志"
              onClick={clearLogs}
            >
              <Trash2 size={15} />
            </IconButton>
            <IconButton
              className="log-panel__clear"
              label={isPinned ? "取消钉住日志" : "钉住日志"}
              onClick={toggleDebugMode}
            >
              {isPinned ? <PinOff size={15} /> : <Pin size={15} />}
            </IconButton>
            <IconButton
              className="log-panel__clear"
              label={isPinned ? "退出调试模式" : "收起日志"}
              onClick={closePanel}
            >
              <Minimize2 size={15} />
            </IconButton>
          </div>
        </div>
        <p className="log-panel__hint">
          {isPinned ? "调试模式已开启" : "最近任务事件"}
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
          <AnimatePresence initial={false}>
            {events.map((event, index) => {
              const key = `${event.timestamp}-${event.source_id}-${index}`;
              const message = logText(event);
              const canExpand = message.length > COLLAPSE_THRESHOLD || message.includes("\n");
              const isExpandedLog = expandedLogs.has(key);
              const eventToneValue = eventTone(event);

              return (
                <motion.article
                  animate={{ opacity: 1, y: 0 }}
                  className={`log-entry log-entry--${eventToneValue} ${isExpandedLog ? "log-entry--expanded" : ""}`}
                  initial={{ opacity: 0, y: 8 }}
                  key={key}
                  transition={{ duration: 0.18, ease: "easeOut" }}
                >
                  <div className="log-entry__meta">
                    <span className="log-entry__tone" aria-hidden="true" />
                    <time>{formatTime(event.timestamp)}</time>
                    <strong title={sourceLabels.get(event.source_id) ?? event.source_id}>
                      {sourceLabels.get(event.source_id) ?? event.source_id}
                    </strong>
                    <span className="log-entry__type">{eventLabel(event)}</span>
                  </div>
                  <p className={`log-entry__message ${canExpand && !isExpandedLog ? "log-entry__message--collapsed" : ""}`}>
                    {message}
                  </p>
                  {canExpand ? (
                    <button
                      className="log-entry__toggle"
                      onClick={() => toggleLog(key)}
                      type="button"
                    >
                      {isExpandedLog ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      <span>{isExpandedLog ? "收起" : "展开"}</span>
                    </button>
                  ) : null}
                </motion.article>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </motion.aside>
  );

  return (
    <>
      <AnimatePresence initial={false}>
        {isPanelOpen ? renderFullPanel() : null}
      </AnimatePresence>
      <AnimatePresence initial={false}>
        {!isPanelOpen && shouldShowDock ? renderTicker("dock") : null}
      </AnimatePresence>
      <AnimatePresence initial={false}>
        {!isPanelOpen && !shouldShowDock ? renderTicker("capsule") : null}
      </AnimatePresence>
    </>
  );
}
