import {
  createContext,
  type Dispatch,
  type ReactNode,
  useContext,
  useMemo,
  useReducer
} from "react";
import type {
  ApiConfig,
  LocalConfigWarning,
  PromptTemplate,
  TaskEvent,
  TaskRecord,
  TaskStatus,
  UserSettings,
  WorkflowPromptConfig
} from "../api/types";

export type ViewKey =
  | "novel"
  | "article"
  | "custom"
  | "splitter"
  | "trigger_scan"
  | "prompts"
  | "apis";

interface AppState {
  activeView: ViewKey;
  apiConfigs: ApiConfig[];
  userSettings: UserSettings;
  prompts: PromptTemplate[];
  workflowPromptConfig: WorkflowPromptConfig | null;
  tasks: Record<string, TaskRecord>;
  taskOrder: string[];
  sessionTaskIds: string[];
  events: TaskEvent[];
  apiEvents: Record<string, TaskEvent[]>;
  isLoadingConfig: boolean;
  errorMessage: string | null;
  localConfigWarnings: LocalConfigWarning[];
}

type AppAction =
  | { type: "set_view"; view: ViewKey }
  | { type: "set_api_configs"; items: ApiConfig[] }
  | { type: "set_user_settings"; settings: UserSettings }
  | { type: "set_prompts"; items: PromptTemplate[] }
  | { type: "set_workflow_prompt_config"; config: WorkflowPromptConfig | null }
  | { type: "restore_tasks"; items: TaskRecord[] }
  | { type: "upsert_task"; task: TaskRecord }
  | { type: "append_event"; event: TaskEvent }
  | { type: "clear_events" }
  | { type: "set_loading_config"; value: boolean }
  | { type: "set_error"; message: string | null }
  | { type: "set_local_config_warnings"; warnings: LocalConfigWarning[] }
  | { type: "clear_error_if"; message: string };

const MAX_EVENTS = 600;
const viewKeys: ViewKey[] = [
  "novel",
  "article",
  "custom",
  "splitter",
  "trigger_scan",
  "prompts",
  "apis"
];

const baseInitialState: AppState = {
  activeView: "novel",
  apiConfigs: [],
  userSettings: { default_export_directory: "", minimum_output_characters: 0 },
  prompts: [],
  workflowPromptConfig: null,
  tasks: {},
  taskOrder: [],
  sessionTaskIds: [],
  events: [],
  apiEvents: {},
  isLoadingConfig: false,
  errorMessage: null,
  localConfigWarnings: []
};

function isViewKey(value: string | null): value is ViewKey {
  return Boolean(value && viewKeys.includes(value as ViewKey));
}

function createVisualEvent(
  taskId: string,
  index: number,
  message: string,
  status: TaskStatus | string | null = "running",
  data: Record<string, unknown> = {}
): TaskEvent {
  return {
    task_id: taskId,
    event_type: data.stages ? "progress" : "log",
    message,
    source_id: index % 3 === 0 ? "visual-api-b" : "visual-api-a",
    event_id: index,
    status,
    progress_text: message,
    data,
    timestamp: Date.now() + index
  };
}

function createVisualTask(
  status: TaskStatus,
  overrides: Partial<TaskRecord> = {}
): TaskRecord {
  const taskId = overrides.task_id ?? `visual-${status}`;
  const progressEvent = createVisualEvent(taskId, 1, "正在整理章节与阶段状态", status, {
    current_stage: status === "success" || status === "partial_failed" ? "final" : "big",
    stages: [
      { id: "small", label: "小总结", completed: 12, total: 12, status: "completed" },
      {
        id: "big",
        label: "大总结",
        completed: status === "success" || status === "partial_failed" ? 6 : 3,
        total: 6,
        status: status === "running" || status === "paused" ? "running" : "completed"
      },
      {
        id: "super",
        label: "超级总结",
        completed: status === "success" || status === "partial_failed" ? 2 : 0,
        total: 2,
        status: status === "success" || status === "partial_failed" ? "completed" : "pending"
      },
      {
        id: "final",
        label: "最终总结",
        completed: status === "success" || status === "partial_failed" ? 1 : 0,
        total: 1,
        status: status === "success" || status === "partial_failed" ? "completed" : "pending"
      }
    ]
  });

  return {
    task_id: taskId,
    task_type: "novel_summary",
    status,
    progress_text: status === "running" ? "正在生成大总结草稿" : "任务状态已写入视觉检查 fixture",
    created_at: Date.now() - 120000,
    updated_at: Date.now(),
    finished_at: status === "running" || status === "paused" ? null : Date.now(),
    result_summary: status === "success" ? "exports/visual/final_summary.md" : null,
    error: status === "failed" ? "输出目录不可写，已保留可恢复状态。" : null,
    warnings: [],
    result_data: {},
    params_summary: { project_slug: "visual-loaded-project" },
    events: [progressEvent],
    ...overrides
  };
}

function createVisualApiConfigs(): ApiConfig[] {
  return [
    {
      id: "visual-api-a",
      display_name: "Studio Primary",
      url: "https://api.example.test/v1",
      key: "",
      model: "narrative-pro",
      max_tokens: 8192,
      temperature: 0.55,
      stream: true,
      timeout: 180,
      max_retries: 3,
      is_active: true,
      key_env_var: "STUDIO_PRIMARY_KEY",
      has_key: true,
      has_env_key: true
    },
    {
      id: "visual-api-b",
      display_name: "Review Backup",
      url: "https://backup.example.test/v1",
      key: "",
      model: "reviewer-lite",
      max_tokens: 4096,
      temperature: 0.3,
      stream: false,
      timeout: 120,
      max_retries: 2,
      is_active: true,
      key_env_var: "STUDIO_REVIEW_KEY",
      has_key: false,
      has_env_key: true
    }
  ];
}

function createVisualInitialState(base: AppState): AppState {
  if (!import.meta.env.DEV || typeof window === "undefined") {
    return base;
  }

  const params = new URLSearchParams(window.location.search);
  const fixture = params.get("studioVisualFixture") ?? "";
  const requestedView = params.get("view");
  const activeView = isViewKey(requestedView) ? requestedView : base.activeView;

  if (!fixture) {
    return { ...base, activeView };
  }

  if (fixture === "empty") {
    return {
      ...base,
      activeView,
      apiConfigs: createVisualApiConfigs()
    };
  }

  const runningTask = createVisualTask("running");
  const successTask = createVisualTask("success", {
    task_id: "visual-terminal",
    task_type: "article_summary",
    progress_text: "最终总结已完成",
    result_summary: "exports/article/final.md"
  });
  const repairTask = createVisualTask("failed", {
    task_id: "visual-repair-warning",
    task_type: "project_repair",
    progress_text: "项目修复需要确认覆盖策略",
    warnings: [
      "检测到旧版输出目录与当前项目设置不一致。",
      "继续修复前需要确认是否允许覆盖已存在的阶段产物。"
    ]
  });
  const triggerTask = createVisualTask("success", {
    task_id: "visual-trigger-report",
    task_type: "trigger_scan",
    progress_text: "雷点报告已进入复核阶段",
    result_summary: "42 条发现 · 7 条待复核",
    params_summary: { project_slug: "visual-trigger-project", report_id: "report-visual-001" }
  });
  const logTask = createVisualTask("running", {
    task_id: "visual-log-heavy",
    task_type: "custom_summary",
    progress_text: "正在处理长日志会话"
  });

  const taskByFixture: Record<string, TaskRecord> = {
    running: runningTask,
    loaded: runningTask,
    terminal: successTask,
    "repair-warning": repairTask,
    "trigger-report": triggerTask,
    "log-heavy": logTask
  };
  const task = taskByFixture[fixture] ?? runningTask;
  const denseEvents =
    fixture === "log-heavy"
      ? Array.from({ length: 48 }, (_, index) =>
          createVisualEvent(
            task.task_id,
            index + 2,
            `视觉检查日志 ${String(index + 1).padStart(2, "0")}：已接收 API 分片并更新工作台反馈。`,
            task.status
          )
        )
      : task.events;

  return {
    ...base,
    activeView,
    apiConfigs: createVisualApiConfigs(),
    userSettings: {
      default_export_directory: "H:/NovelSummaryAssistant/exports/visual",
      minimum_output_characters: 120
    },
    tasks: { [task.task_id]: { ...task, events: denseEvents } },
    taskOrder: [task.task_id],
    sessionTaskIds: [
      "running",
      "loaded",
      "terminal",
      "repair-warning",
      "trigger-report",
      "log-heavy"
    ].includes(fixture)
      ? [task.task_id]
      : [],
    events: denseEvents,
    apiEvents: denseEvents.reduce<Record<string, TaskEvent[]>>((items, event) => {
      items[event.source_id] = [...(items[event.source_id] ?? []), event];
      return items;
    }, {}),
    localConfigWarnings:
      fixture === "repair-warning"
        ? [
            {
              domain: "project_repair",
              message: "视觉检查：项目存在可恢复警告，修复前请核对输出目录。",
              path: "visual-project.json",
              backup_path: "visual-project.json.bak",
              backup_failed: false
            }
          ]
        : base.localConfigWarnings
  };
}

function limitEvents(events: TaskEvent[]) {
  return events.length > MAX_EVENTS ? events.slice(events.length - MAX_EVENTS) : events;
}

function prependUnique(items: string[], item: string) {
  return [item, ...items.filter((existingItem) => existingItem !== item)];
}

function normalizeTaskRecord(task: TaskRecord): TaskRecord {
  return {
    ...task,
    warnings: Array.isArray(task.warnings) ? task.warnings : [],
    result_data:
      task.result_data && typeof task.result_data === "object" && !Array.isArray(task.result_data)
        ? task.result_data
        : {}
  };
}

function upsertTask(state: AppState, task: TaskRecord): AppState {
  const normalizedTask = normalizeTaskRecord(task);
  const exists = Boolean(state.tasks[task.task_id]);
  return {
    ...state,
    tasks: { ...state.tasks, [normalizedTask.task_id]: normalizedTask },
    taskOrder: exists ? state.taskOrder : [normalizedTask.task_id, ...state.taskOrder],
    sessionTaskIds: prependUnique(state.sessionTaskIds, normalizedTask.task_id)
  };
}

function isTaskStatus(value: TaskEvent["status"]): value is TaskStatus {
  return (
    value === "pending" ||
    value === "running" ||
    value === "paused" ||
    value === "canceling" ||
    value === "cancelled" ||
    value === "partial_failed" ||
    value === "success" ||
    value === "failed" ||
    value === "interrupted"
  );
}

function appendTaskEvent(state: AppState, event: TaskEvent): AppState {
  const existingTask = state.tasks[event.task_id];
  const nextTask = existingTask
    ? {
        ...existingTask,
        status: isTaskStatus(event.status) ? event.status : existingTask.status,
        progress_text: event.progress_text ?? existingTask.progress_text,
        events: limitEvents([...existingTask.events, event])
      }
    : existingTask;
  const sourceId = event.source_id || "global";
  const nextApiEvents = {
    ...state.apiEvents,
    [sourceId]: limitEvents([...(state.apiEvents[sourceId] ?? []), event])
  };

  return {
    ...state,
    tasks: nextTask ? { ...state.tasks, [event.task_id]: nextTask } : state.tasks,
    sessionTaskIds: nextTask ? prependUnique(state.sessionTaskIds, event.task_id) : state.sessionTaskIds,
    events: limitEvents([...state.events, event]),
    apiEvents: nextApiEvents
  };
}

function restoreTasks(state: AppState, tasks: TaskRecord[]): AppState {
  const taskMap = { ...state.tasks };
  const existingOrder = state.taskOrder.filter((taskId) => !tasks.some((task) => task.task_id === taskId));
  const restoredOrder = tasks.map((task) => task.task_id);
  const busyStatuses = new Set(["pending", "running", "paused", "canceling"]);
  const restoredActiveTaskIds = tasks
    .filter((task) => busyStatuses.has(task.status))
    .map((task) => task.task_id);
  const nextSessionTaskIds = restoredActiveTaskIds.reduceRight(
    (items, taskId) => prependUnique(items, taskId),
    state.sessionTaskIds
  );
  const restoredEvents = tasks
    .filter((task) => busyStatuses.has(task.status))
    .flatMap((task) => task.events)
    .sort((left, right) => left.timestamp - right.timestamp);
  const nextApiEvents: Record<string, TaskEvent[]> = {};

  tasks.forEach((task) => {
    const normalizedTask = normalizeTaskRecord(task);
    taskMap[normalizedTask.task_id] = normalizedTask;
  });
  restoredEvents.forEach((event) => {
    const sourceId = event.source_id || "global";
    nextApiEvents[sourceId] = limitEvents([...(nextApiEvents[sourceId] ?? []), event]);
  });

  return {
    ...state,
    tasks: taskMap,
    taskOrder: [...restoredOrder, ...existingOrder],
    sessionTaskIds: nextSessionTaskIds,
    events: limitEvents(restoredEvents),
    apiEvents: nextApiEvents
  };
}

function reducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "set_view":
      return { ...state, activeView: action.view };
    case "set_api_configs":
      return { ...state, apiConfigs: action.items };
    case "set_user_settings":
      return { ...state, userSettings: action.settings };
    case "set_prompts":
      return { ...state, prompts: action.items };
    case "set_workflow_prompt_config":
      return { ...state, workflowPromptConfig: action.config };
    case "restore_tasks":
      return restoreTasks(state, action.items);
    case "upsert_task":
      return upsertTask(state, action.task);
    case "append_event":
      return appendTaskEvent(state, action.event);
    case "clear_events":
      return { ...state, events: [], apiEvents: {} };
    case "set_loading_config":
      return { ...state, isLoadingConfig: action.value };
    case "set_error":
      return { ...state, errorMessage: action.message };
    case "set_local_config_warnings":
      return { ...state, localConfigWarnings: action.warnings };
    case "clear_error_if":
      return state.errorMessage === action.message
        ? { ...state, errorMessage: null }
        : state;
    default:
      return state;
  }
}

interface AppStateContextValue {
  state: AppState;
  dispatch: Dispatch<AppAction>;
}

const AppStateContext = createContext<AppStateContextValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(
    reducer,
    baseInitialState,
    createVisualInitialState
  );
  const value = useMemo(() => ({ state, dispatch }), [state]);

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const value = useContext(AppStateContext);
  if (!value) {
    throw new Error("useAppState must be used inside AppStateProvider");
  }
  return value;
}
