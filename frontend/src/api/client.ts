import type {
  ApiConfig,
  ApiListResponse,
  ArticleSummaryRequest,
  BrowsePathResponse,
  CustomSummaryRequest,
  DeleteProjectResponse,
  ModelListResponse,
  OpenDirectoryResponse,
  ProjectListResponse,
  ProjectRecord,
  PromptMessage,
  NovelSummaryRequest,
  PromptListResponse,
  PromptModule,
  PromptTemplate,
  PromptNode,
  ResolvePathResponse,
  SplitterRequest,
  TaskEvent,
  TaskListResponse,
  TaskRecord,
  UploadResponse,
  UploadTextFile,
  UserSettings,
  WorkflowType,
  WorkflowPromptConfig
} from "./types";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `请求失败：${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, {
    ...init,
    headers
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data?.detail ?? data ?? response.statusText;
    throw new ApiError(response.status, detail);
  }
  return data as T;
}

function postJson<TResponse, TBody extends object>(
  path: string,
  body: TBody
): Promise<TResponse> {
  return requestJson<TResponse>(path, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export const apiClient = {
  health: () => requestJson<{ status: string }>("/api/health"),

  loadApiConfigs: async () => {
    const response = await requestJson<ApiListResponse>("/api/config/api");
    return response.items;
  },

  saveApiConfigs: async (items: ApiConfig[]) => {
    const response = await postJson<ApiListResponse, ApiConfig[]>("/api/config/api", items);
    return response.items;
  },

  loadUserSettings: () => requestJson<UserSettings>("/api/settings"),

  saveUserSettings: (settings: UserSettings) =>
    postJson<UserSettings, UserSettings>("/api/settings", settings),

  clearDefaultExportDirectory: () =>
    requestJson<UserSettings>("/api/settings/default-export-directory", {
      method: "DELETE"
    }),

  loadPrompts: async () => {
    const response = await requestJson<PromptListResponse>("/api/prompts");
    return response.items;
  },

  loadPromptConfig: () => requestJson<PromptListResponse>("/api/prompts"),

  savePrompt: (promptKey: string, text: string) =>
    postJson<PromptTemplate, { text: string }>(`/api/prompts/${promptKey}`, { text }),

  resetPrompt: (promptKey: string) =>
    postJson<PromptTemplate, Record<string, never>>(
      `/api/prompts/${promptKey}/reset`,
      {}
    ),

  savePromptNode: (promptKey: string, messages: PromptMessage[]) =>
    postJson<PromptNode, { messages: PromptMessage[] }>(
      `/api/prompts/nodes/${promptKey}`,
      { messages }
    ),

  resetPromptNode: (promptKey: string) =>
    postJson<PromptNode, Record<string, never>>(
      `/api/prompts/nodes/${promptKey}/reset`,
      {}
    ),

  savePromptModule: (module: PromptModule) =>
    postJson<WorkflowPromptConfig, PromptModule>("/api/prompts/modules", module),

  deletePromptModule: (moduleId: string) =>
    requestJson<WorkflowPromptConfig>(`/api/prompts/modules/${moduleId}`, {
      method: "DELETE"
    }),

  fetchModels: async (config: ApiConfig) => {
    const response = await postJson<ModelListResponse, ApiConfig>("/api/models", config);
    return response.items;
  },

  pickDirectory: async (title: string) => {
    const response = await postJson<BrowsePathResponse, { title: string }>(
      "/api/browse/directory",
      { title }
    );
    return response.path;
  },

  resolvePath: (path: string) =>
    postJson<ResolvePathResponse, { path: string }>("/api/utils/resolve-path", { path }),

  uploadTextFiles: (
    projectName: string,
    workflowType: WorkflowType,
    files: UploadTextFile[],
    projectSlug = ""
  ) =>
    postJson<
      UploadResponse,
      {
        project_name: string;
        project_slug?: string;
        workflow_type: WorkflowType;
        files: UploadTextFile[];
      }
    >("/api/uploads", {
      project_name: projectName,
      project_slug: projectSlug || undefined,
      workflow_type: workflowType,
      files
    }),

  listProjects: async (workflowType?: WorkflowType) => {
    const suffix = workflowType ? `?workflow_type=${encodeURIComponent(workflowType)}` : "";
    const response = await requestJson<ProjectListResponse>(`/api/projects${suffix}`);
    return response.items;
  },

  getProject: (projectSlug: string) =>
    requestJson<ProjectRecord>(`/api/projects/${encodeURIComponent(projectSlug)}`),

  updateProjectName: (projectSlug: string, projectName: string) =>
    requestJson<ProjectRecord>(`/api/projects/${encodeURIComponent(projectSlug)}`, {
      method: "PATCH",
      body: JSON.stringify({ project_name: projectName })
    }),

  deleteProject: (projectSlug: string) =>
    requestJson<DeleteProjectResponse>(`/api/projects/${encodeURIComponent(projectSlug)}`, {
      method: "DELETE"
    }),

  importProject: (path: string, workflowType: WorkflowType, projectName = "") =>
    postJson<
      ProjectRecord,
      { path: string; workflow_type: WorkflowType; project_name?: string }
    >("/api/projects/import", {
      path,
      workflow_type: workflowType,
      project_name: projectName || undefined
    }),

  clearProjectUploads: (projectSlug: string) =>
    requestJson<ProjectRecord>(`/api/projects/${encodeURIComponent(projectSlug)}/uploads`, {
      method: "DELETE"
    }),

  openDirectory: (request: {
    project_slug?: string;
    workflow_type?: WorkflowType;
    custom_output_directory_path?: string;
    path?: string;
  }) =>
    postJson<OpenDirectoryResponse, typeof request>("/api/projects/open-directory", request),

  startNovelSummary: (request: NovelSummaryRequest) =>
    postJson<TaskRecord, NovelSummaryRequest>("/api/tasks/novel", request),

  startArticleSummary: (request: ArticleSummaryRequest) =>
    postJson<TaskRecord, ArticleSummaryRequest>("/api/tasks/article", request),

  startCustomSummary: (request: CustomSummaryRequest) =>
    postJson<TaskRecord, CustomSummaryRequest>("/api/tasks/custom", request),

  startSplitter: (request: SplitterRequest) =>
    postJson<TaskRecord, SplitterRequest>("/api/tasks/splitter", request),

  listTasks: async () => {
    const response = await requestJson<TaskListResponse>("/api/tasks");
    return response.items;
  },

  getTask: (taskId: string) => requestJson<TaskRecord>(`/api/tasks/${taskId}`),

  pauseTask: (taskId: string) =>
    postJson<TaskRecord, Record<string, never>>(`/api/tasks/${taskId}/pause`, {}),

  resumeTask: (taskId: string) =>
    postJson<TaskRecord, Record<string, never>>(`/api/tasks/${taskId}/resume`, {}),

  cancelTask: (taskId: string) =>
    postJson<TaskRecord, Record<string, never>>(`/api/tasks/${taskId}/cancel`, {})
};

export interface TaskEventSubscription {
  close: () => void;
}

export function subscribeTaskEvents(
  taskId: string,
  handlers: {
    onEvent: (event: TaskEvent) => void;
    onError?: (error: Event) => void;
  }
): TaskEventSubscription {
  const eventSource = new EventSource(`/api/tasks/${taskId}/events`);
  eventSource.onmessage = (event) => {
    handlers.onEvent(JSON.parse(event.data) as TaskEvent);
  };
  eventSource.onerror = (event) => {
    handlers.onError?.(event);
  };
  return {
    close: () => eventSource.close()
  };
}
