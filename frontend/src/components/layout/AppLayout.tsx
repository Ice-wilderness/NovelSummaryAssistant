import {
  BookOpen,
  FileText,
  ListTree,
  LoaderCircle,
  MessageSquareText,
  PanelLeft,
  Pause,
  Play,
  Scissors,
  ScrollText,
  ServerCog,
  ShieldAlert,
  Square,
  TriangleAlert
} from "lucide-react";
import type { ReactNode } from "react";
import { apiClient } from "../../api/client";
import { useTaskAvailability } from "../../hooks/useTaskAvailability";
import { useAppState, type ViewKey } from "../../state/AppState";
import { IconButton } from "../common/IconButton";
import { LogPanel } from "../logs/LogPanel";

const navItems: Array<{
  key: ViewKey;
  label: string;
  icon: typeof BookOpen;
}> = [
  { key: "novel", label: "小说总结", icon: BookOpen },
  { key: "article", label: "文章总结", icon: FileText },
  { key: "custom", label: "自定义总结", icon: MessageSquareText },
  { key: "splitter", label: "章节分割", icon: Scissors },
  { key: "trigger_scan", label: "雷点扫描", icon: ShieldAlert },
  { key: "prompts", label: "提示词", icon: ScrollText },
  { key: "apis", label: "API 配置", icon: ServerCog }
];

const viewTitles: Record<ViewKey, string> = {
  novel: "小说总结",
  article: "文章总结",
  custom: "自定义总结",
  splitter: "章节分割",
  trigger_scan: "雷点扫描",
  prompts: "提示词",
  apis: "API 配置"
};

function statusLabel(status?: string) {
  switch (status) {
    case "running":
      return "运行中";
    case "paused":
      return "已暂停";
    case "canceling":
      return "取消中";
    case "cancelled":
      return "已取消";
    case "success":
      return "已完成";
    case "partial_failed":
      return "部分结果";
    case "failed":
      return "失败";
    case "interrupted":
      return "已中断";
    default:
      return "空闲";
  }
}

export function AppLayout({ children }: { children: ReactNode }) {
  const { state, dispatch } = useAppState();
  const { latestTask } = useTaskAvailability();
  const canPause = latestTask?.status === "running";
  const canResume = latestTask?.status === "paused";
  const canCancel =
    latestTask?.status === "pending" ||
    latestTask?.status === "running" ||
    latestTask?.status === "paused";
  const terminalMessage =
    latestTask?.status === "success"
      ? latestTask.result_summary || "任务已完成"
      : latestTask?.status === "failed"
        ? latestTask.error || "任务失败"
        : latestTask?.status === "partial_failed"
          ? latestTask.error || latestTask.result_summary || "任务部分完成，已保留可用结果"
          : latestTask?.status === "cancelled"
            ? "任务已取消"
            : latestTask?.status === "interrupted"
              ? latestTask.error || latestTask.warnings[0] || "后端重启前任务未结束，请重新启动或从项目进度继续"
              : "";

  const controlTask = async (action: "pause" | "resume" | "cancel") => {
    if (!latestTask) {
      return;
    }
    try {
      const updatedTask =
        action === "pause"
          ? await apiClient.pauseTask(latestTask.task_id)
          : action === "resume"
            ? await apiClient.resumeTask(latestTask.task_id)
            : await apiClient.cancelTask(latestTask.task_id);
      dispatch({ type: "upsert_task", task: updatedTask });
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      dispatch({
        type: "set_error",
        message: error instanceof Error ? error.message : String(error)
      });
    }
  };

  return (
    <div className="workbench">
      <aside className="sidebar">
        <div className="brand-block">
          <PanelLeft size={22} />
          <div>
            <strong>NovelSummaryAssistant</strong>
            <span>WebUI</span>
          </div>
        </div>
        <nav className="side-nav" aria-label="主导航">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                aria-current={state.activeView === item.key ? "page" : undefined}
                className="nav-button"
                key={item.key}
                onClick={() => dispatch({ type: "set_view", view: item.key })}
                type="button"
              >
                <Icon size={19} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
        <section className="attribution" aria-label="项目署名">
          <span>原作者：zhoufei_1314</span>
          <span>现作者：Ice_wilderness</span>
        </section>
      </aside>

      <section className="main-region">
        <header className="topbar">
          <div>
            <h1>{viewTitles[state.activeView]}</h1>
            <p>{latestTask?.progress_text || latestTask?.result_summary || "任务待命"}</p>
          </div>
          <div className="task-controls">
            <span className={`status-pill status-pill--${latestTask?.status ?? "idle"}`}>
              {statusLabel(latestTask?.status)}
            </span>
            <IconButton
              disabled={!canResume}
              label="恢复"
              onClick={() => void controlTask("resume")}
              variant="primary"
            >
              <Play size={18} />
            </IconButton>
            <IconButton disabled={!canPause} label="暂停" onClick={() => void controlTask("pause")}>
              <Pause size={18} />
            </IconButton>
            <IconButton
              disabled={!canCancel}
              label="取消"
              onClick={() => void controlTask("cancel")}
              variant="danger"
            >
              <Square size={17} />
            </IconButton>
          </div>
        </header>

        {state.errorMessage ? (
          <button
            aria-label="关闭提示"
            className="global-message-toast global-message-toast--error"
            onClick={() => dispatch({ type: "set_error", message: null })}
            type="button"
          >
            <TriangleAlert size={18} />
            <span>{state.errorMessage}</span>
          </button>
        ) : null}

        {state.isLoadingConfig || terminalMessage ? (
          <section
            className={`system-banner ${terminalMessage ? "system-banner--done" : ""}`}
          >
            {state.isLoadingConfig ? (
              <LoaderCircle className="spin-icon" size={17} />
            ) : (
              <ListTree size={17} />
            )}
            <span>
              {state.isLoadingConfig ? "配置加载中" : terminalMessage}
            </span>
          </section>
        ) : null}

        <main className="workspace-main">{children}</main>
      </section>

      <LogPanel />
    </div>
  );
}
