import {
  BookOpen,
  FileText,
  FolderClock,
  Gauge,
  Layers3,
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
  TriangleAlert,
  WandSparkles
} from "lucide-react";
import type { ReactNode } from "react";
import { apiClient } from "../../api/client";
import { useTaskAvailability } from "../../hooks/useTaskAvailability";
import { useAppState, type ViewKey } from "../../state/AppState";
import { IconButton } from "../common/IconButton";
import { LogPanel } from "../logs/LogPanel";
import {
  StudioPanel,
  StudioStatusBadge
} from "../studio/StudioPrimitives";
import { StudioStageFlow } from "../studio/StudioStageFlow";
import {
  taskHeadline,
  taskStatusLabel,
  taskStatusTone,
  taskTerminalMessage,
  taskTypeLabel
} from "../studio/taskPresentation";

const navItems: Array<{
  key: ViewKey;
  label: string;
  meta: string;
  icon: typeof BookOpen;
}> = [
  { key: "novel", label: "小说总结", meta: "项目 · 章节 · 阶段", icon: BookOpen },
  { key: "article", label: "文章总结", meta: "文档 · 结果", icon: FileText },
  { key: "custom", label: "自定义总结", meta: "文件 · Prompt", icon: MessageSquareText },
  { key: "splitter", label: "章节分割", meta: "TXT · 预览", icon: Scissors },
  { key: "trigger_scan", label: "雷点扫描", meta: "档案 · 报告", icon: ShieldAlert },
  { key: "prompts", label: "提示词", meta: "节点 · 模块", icon: ScrollText },
  { key: "apis", label: "API 配置", meta: "模型 · 密钥", icon: ServerCog }
];

const viewGuidance: Record<ViewKey, { title: string; intro: string; actions: string[] }> = {
  novel: {
    title: "组织小说项目",
    intro: "围绕项目、章节、输出目录和总结阶段推进，适合长篇任务的连续工作。",
    actions: ["选择或导入项目", "上传源 TXT 并预览分割", "确认 API 与任务参数", "启动总结或修复产物"]
  },
  article: {
    title: "处理文章批次",
    intro: "把短文档、输出目录和字数配置放在同一条路径里，快速得到结果。",
    actions: ["上传文章文件", "检查输出目录", "确认字数设置", "启动文章总结"]
  },
  custom: {
    title: "执行自定义总结",
    intro: "用指定 API 与自定义提示词处理选中文件，适合一次性专题整理。",
    actions: ["上传待处理文件", "选择 API", "编写提示词", "启动并查看结果"]
  },
  splitter: {
    title: "拆分章节文件",
    intro: "先预览章节识别结果，再导出或导入到项目，降低分割错误成本。",
    actions: ["选择 TXT 源文件", "配置分割模式", "预览章节边界", "确认输出位置"]
  },
  trigger_scan: {
    title: "复核雷点报告",
    intro: "把档案维护、扫描配置、实时发现和报告复核串在一个审阅工作流里。",
    actions: ["选择项目和档案", "运行预检", "启动或续扫", "筛选并复核结果"]
  },
  prompts: {
    title: "维护提示词系统",
    intro: "编辑工作流节点与模块，保存前保留草稿状态，便于逐段调整。",
    actions: ["选择工作流", "编辑节点消息", "调整复用模块", "保存提示词配置"]
  },
  apis: {
    title: "配置模型通道",
    intro: "管理可用 API、模型列表、密钥状态和默认导出目录。",
    actions: ["检查配置恢复提示", "启用或禁用 API", "拉取模型列表", "保存全局设置"]
  }
};

function compactId(value: string) {
  return value.length > 10 ? `${value.slice(0, 6)}...${value.slice(-4)}` : value;
}

export function AppLayout({ children }: { children: ReactNode }) {
  const { state, dispatch } = useAppState();
  const { latestTask } = useTaskAvailability();
  const activeMeta = viewGuidance[state.activeView];
  const activeApis = state.apiConfigs.filter((config) => config.is_active);
  const canPause = latestTask?.status === "running";
  const canResume = latestTask?.status === "paused";
  const canCancel =
    latestTask?.status === "pending" ||
    latestTask?.status === "running" ||
    latestTask?.status === "paused";
  const terminalMessage = taskTerminalMessage(latestTask);
  const taskProjectSlug =
    typeof latestTask?.params_summary.project_slug === "string"
      ? latestTask.params_summary.project_slug
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
    <div className="studio-workbench">
      <aside className="studio-sidebar">
        <div className="studio-brand">
          <PanelLeft size={21} />
          <div>
            <strong>NovelSummaryAssistant</strong>
            <span>Writing Studio</span>
          </div>
        </div>

        <nav className="studio-nav" aria-label="主导航">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = state.activeView === item.key;
            return (
              <button
                aria-current={isActive ? "page" : undefined}
                className="studio-nav__item"
                key={item.key}
                onClick={() => dispatch({ type: "set_view", view: item.key })}
                type="button"
              >
                <Icon size={18} />
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.meta}</small>
                </span>
              </button>
            );
          })}
        </nav>

        <StudioPanel
          className="studio-context-index"
          description="这里保留全局上下文，页面内会继续展示项目、章节、报告或配置细节。"
          title="工作室索引"
        >
          <div className="studio-context-grid">
            <div
              className="studio-context-stat"
              data-tone={activeApis.length > 0 ? "success" : "warning"}
            >
              <span>启用 API</span>
              <strong>{activeApis.length}</strong>
            </div>
            <div
              className="studio-context-stat"
              data-tone={state.sessionTaskIds.length > 0 ? "primary" : "muted"}
            >
              <span>会话任务</span>
              <strong>{state.sessionTaskIds.length}</strong>
            </div>
            <div
              className="studio-context-stat"
              data-tone={state.events.length > 0 ? "primary" : "muted"}
            >
              <span>全局日志</span>
              <strong>{state.events.length}</strong>
            </div>
            <div
              className="studio-context-stat"
              data-tone={state.localConfigWarnings.length > 0 ? "warning" : "muted"}
            >
              <span>配置提示</span>
              <strong>{state.localConfigWarnings.length}</strong>
            </div>
          </div>
        </StudioPanel>

        <section className="studio-attribution" aria-label="项目署名">
          <span>原作者：zhoufei_1314</span>
          <span>现作者：Ice_wilderness</span>
        </section>
      </aside>

      <section className="studio-shell">
        <header className="studio-topbar">
          <div className="studio-topbar__identity">
            <span className="studio-eyebrow">
              <WandSparkles size={15} />
              Studio Workbench
            </span>
            <h1>{navItems.find((item) => item.key === state.activeView)?.label}</h1>
            <p>{taskHeadline(latestTask)}</p>
          </div>
          <div className="studio-task-console" aria-label="当前任务控制">
            <div className="studio-task-console__state">
              <StudioStatusBadge tone={taskStatusTone(latestTask?.status)}>
                {taskStatusLabel(latestTask?.status)}
              </StudioStatusBadge>
              <span>{latestTask ? taskTypeLabel(latestTask.task_type) : "无运行任务"}</span>
            </div>
            <div className="studio-task-console__buttons">
              <IconButton
                className="studio-task-button"
                disabled={!canResume}
                label="恢复"
                onClick={() => void controlTask("resume")}
                variant="primary"
              >
                <Play size={18} />
              </IconButton>
              <IconButton
                className="studio-task-button"
                disabled={!canPause}
                label="暂停"
                onClick={() => void controlTask("pause")}
              >
                <Pause size={18} />
              </IconButton>
              <IconButton
                className="studio-task-button"
                disabled={!canCancel}
                label="取消"
                onClick={() => void controlTask("cancel")}
                variant="danger"
              >
                <Square size={17} />
              </IconButton>
            </div>
          </div>
        </header>

        {state.errorMessage ? (
          <button
            aria-label="关闭提示"
            className="global-message-toast global-message-toast--error studio-message-toast"
            onClick={() => dispatch({ type: "set_error", message: null })}
            type="button"
          >
            <TriangleAlert size={18} />
            <span>{state.errorMessage}</span>
          </button>
        ) : null}

        {state.isLoadingConfig || terminalMessage ? (
          <section
            className={`system-banner studio-system-banner ${terminalMessage ? "system-banner--done" : ""}`}
          >
            {state.isLoadingConfig ? (
              <LoaderCircle className="spin-icon" size={17} />
            ) : (
              <Layers3 size={17} />
            )}
            <span>{state.isLoadingConfig ? "配置加载中" : terminalMessage}</span>
          </section>
        ) : null}

        <StudioStageFlow task={latestTask} />

        <div className="studio-body">
          <main className="workspace-main studio-workspace-main">{children}</main>

          <aside className="studio-inspector" aria-label="当前步骤">
            <StudioPanel
              actions={
                <StudioStatusBadge tone={taskStatusTone(latestTask?.status)}>
                  {latestTask ? `步骤：${taskStatusLabel(latestTask.status)}` : "步骤待命"}
                </StudioStatusBadge>
              }
              description={activeMeta.intro}
              title={activeMeta.title}
            >
              <ol className="studio-next-actions">
                {activeMeta.actions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ol>
            </StudioPanel>

            <StudioPanel
              className="studio-current-task"
              description={latestTask ? `进度：${taskHeadline(latestTask)}` : "启动任务后会在这里同步状态、项目和警告。"}
              title="当前任务"
            >
              {latestTask ? (
                <>
                  <div className="studio-task-detail">
                    <Gauge size={16} />
                    <span>{taskTypeLabel(latestTask.task_type)}</span>
                    <strong>{compactId(latestTask.task_id)}</strong>
                  </div>
                  {taskProjectSlug ? (
                    <div className="studio-task-detail">
                      <FolderClock size={16} />
                      <span>项目</span>
                      <strong>{taskProjectSlug}</strong>
                    </div>
                  ) : null}
                  {latestTask.warnings.length > 0 ? (
                    <div className="studio-warning-list">
                      {latestTask.warnings.slice(0, 3).map((warning) => (
                        <span key={warning}>
                          <TriangleAlert size={14} />
                          {warning}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="empty-state">暂无任务警告</span>
                  )}
                </>
              ) : (
                <span className="empty-state">暂无任务</span>
              )}
            </StudioPanel>

            {state.localConfigWarnings.length > 0 ? (
              <StudioPanel className="studio-config-warnings" title="配置恢复提示">
                <div className="studio-warning-list">
                  {state.localConfigWarnings.slice(0, 3).map((warning) => (
                    <span key={`${warning.domain}-${warning.path}`}>
                      <TriangleAlert size={14} />
                      {warning.message}
                    </span>
                  ))}
                </div>
              </StudioPanel>
            ) : null}
          </aside>
        </div>

        <LogPanel />
      </section>
    </div>
  );
}
