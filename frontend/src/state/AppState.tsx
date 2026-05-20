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
  | "prompts"
  | "apis"
  | "logs";

interface AppState {
  activeView: ViewKey;
  apiConfigs: ApiConfig[];
  userSettings: UserSettings;
  prompts: PromptTemplate[];
  workflowPromptConfig: WorkflowPromptConfig | null;
  tasks: Record<string, TaskRecord>;
  taskOrder: string[];
  events: TaskEvent[];
  apiEvents: Record<string, TaskEvent[]>;
  isLoadingConfig: boolean;
  errorMessage: string | null;
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
  | { type: "set_loading_config"; value: boolean }
  | { type: "set_error"; message: string | null };

const MAX_EVENTS = 600;

const initialState: AppState = {
  activeView: "novel",
  apiConfigs: [],
  userSettings: { default_export_directory: "" },
  prompts: [],
  workflowPromptConfig: null,
  tasks: {},
  taskOrder: [],
  events: [],
  apiEvents: {},
  isLoadingConfig: false,
  errorMessage: null
};

function limitEvents(events: TaskEvent[]) {
  return events.length > MAX_EVENTS ? events.slice(events.length - MAX_EVENTS) : events;
}

function upsertTask(state: AppState, task: TaskRecord): AppState {
  const exists = Boolean(state.tasks[task.task_id]);
  return {
    ...state,
    tasks: { ...state.tasks, [task.task_id]: task },
    taskOrder: exists ? state.taskOrder : [task.task_id, ...state.taskOrder]
  };
}

function isTaskStatus(value: TaskEvent["status"]): value is TaskStatus {
  return (
    value === "pending" ||
    value === "running" ||
    value === "paused" ||
    value === "canceling" ||
    value === "cancelled" ||
    value === "success" ||
    value === "failed"
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
    events: limitEvents([...state.events, event]),
    apiEvents: nextApiEvents
  };
}

function restoreTasks(state: AppState, tasks: TaskRecord[]): AppState {
  const taskMap = { ...state.tasks };
  const existingOrder = state.taskOrder.filter((taskId) => !tasks.some((task) => task.task_id === taskId));
  const restoredOrder = tasks.map((task) => task.task_id);
  const restoredEvents = tasks
    .flatMap((task) => task.events)
    .sort((left, right) => left.timestamp - right.timestamp);
  const nextApiEvents: Record<string, TaskEvent[]> = {};

  tasks.forEach((task) => {
    taskMap[task.task_id] = task;
  });
  restoredEvents.forEach((event) => {
    const sourceId = event.source_id || "global";
    nextApiEvents[sourceId] = limitEvents([...(nextApiEvents[sourceId] ?? []), event]);
  });

  return {
    ...state,
    tasks: taskMap,
    taskOrder: [...restoredOrder, ...existingOrder],
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
    case "set_loading_config":
      return { ...state, isLoadingConfig: action.value };
    case "set_error":
      return { ...state, errorMessage: action.message };
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
