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

const initialState: AppState = {
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
  const [state, dispatch] = useReducer(reducer, initialState);
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
