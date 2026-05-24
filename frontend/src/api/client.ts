import type {
  ApiConfig,
  ApiListResponse,
  ArticleSummaryRequest,
  BrowsePathResponse,
  CustomSummaryRequest,
  DeleteProjectResponse,
  DirectSplitRequest,
  DirectSplitResult,
  ModelListResponse,
  NovelSummaryRequest,
  OpenDirectoryResponse,
  OutputMigrationInfo,
  PatternConfig,
  PatternConfigListResponse,
  PatternImportResponse,
  ProjectListResponse,
  ProjectRecord,
  PromptMessage,
  PromptListResponse,
  PromptModule,
  PromptTemplate,
  PromptNode,
  ResolvePathResponse,
  ScanFinding,
  ScanReport,
  SplitPreviewRequest,
  SplitPreviewResult,
  SplitterRequest,
  TaskEvent,
  TaskListResponse,
  TaskRecord,
  TriggerProfile,
  TriggerProfileListResponse,
  TriggerRule,
  TriggerRuleGroup,
  TriggerReviewStatus,
  TriggerScanConfig,
  TriggerScanContextResponse,
  TriggerScanExportResponse,
  TriggerScanPrecheckResponse,
  TriggerScanReportListResponse,
  TriggerScanRequest,
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

function putJson<TResponse, TBody extends object>(
  path: string,
  body: TBody
): Promise<TResponse> {
  return requestJson<TResponse>(path, {
    method: "PUT",
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

  listTriggerProfiles: async () => {
    const response = await requestJson<TriggerProfileListResponse>("/api/trigger-profiles");
    return response.items;
  },

  createTriggerProfile: (request: {
    name: string;
    description?: string;
    from_template?: boolean;
  }) => postJson<TriggerProfile, typeof request>("/api/trigger-profiles", request),

  getTriggerProfile: (profileId: string) =>
    requestJson<TriggerProfile>(`/api/trigger-profiles/${encodeURIComponent(profileId)}`),

  updateTriggerProfile: (
    profileId: string,
    request: Partial<Pick<TriggerProfile, "name" | "description" | "rule_groups" | "rules">>
  ) =>
    requestJson<TriggerProfile>(`/api/trigger-profiles/${encodeURIComponent(profileId)}`, {
      method: "PATCH",
      body: JSON.stringify(request)
    }),

  duplicateTriggerProfile: (
    profileId: string,
    request: { name?: string; description?: string } = {}
  ) =>
    postJson<TriggerProfile, typeof request>(
      `/api/trigger-profiles/${encodeURIComponent(profileId)}/duplicate`,
      request
    ),

  deleteTriggerProfile: (profileId: string) =>
    requestJson<{ status: string; profile_id: string }>(
      `/api/trigger-profiles/${encodeURIComponent(profileId)}`,
      { method: "DELETE" }
    ),

  addTriggerRuleGroup: (profileId: string, request: Pick<TriggerRuleGroup, "name">) =>
    postJson<TriggerProfile, typeof request>(
      `/api/trigger-profiles/${encodeURIComponent(profileId)}/groups`,
      request
    ),

  updateTriggerRuleGroup: (
    profileId: string,
    groupId: string,
    request: Partial<TriggerRuleGroup>
  ) =>
    requestJson<TriggerProfile>(
      `/api/trigger-profiles/${encodeURIComponent(profileId)}/groups/${encodeURIComponent(groupId)}`,
      { method: "PATCH", body: JSON.stringify(request) }
    ),

  deleteTriggerRuleGroup: (profileId: string, groupId: string) =>
    requestJson<TriggerProfile>(
      `/api/trigger-profiles/${encodeURIComponent(profileId)}/groups/${encodeURIComponent(groupId)}`,
      { method: "DELETE" }
    ),

  addTriggerRule: (profileId: string, request: Omit<TriggerRule, "id">) =>
    postJson<TriggerProfile, Omit<TriggerRule, "id">>(
      `/api/trigger-profiles/${encodeURIComponent(profileId)}/rules`,
      request
    ),

  updateTriggerRule: (
    profileId: string,
    ruleId: string,
    request: Partial<TriggerRule>
  ) =>
    requestJson<TriggerProfile>(
      `/api/trigger-profiles/${encodeURIComponent(profileId)}/rules/${encodeURIComponent(ruleId)}`,
      { method: "PATCH", body: JSON.stringify(request) }
    ),

  deleteTriggerRule: (profileId: string, ruleId: string) =>
    requestJson<TriggerProfile>(
      `/api/trigger-profiles/${encodeURIComponent(profileId)}/rules/${encodeURIComponent(ruleId)}`,
      { method: "DELETE" }
    ),

  importTriggerProfile: (data: {
    name: string;
    description?: string;
    rule_groups?: TriggerRuleGroup[];
    rules?: TriggerRule[];
  }) => postJson<TriggerProfile, typeof data>("/api/trigger-profiles/import", data),

  // ── 正则配置 ────────────────────────────────────────────────

  listPatterns: async () => {
    const response = await requestJson<PatternConfigListResponse>("/api/patterns");
    return response.items;
  },

  createPattern: (data: { name: string; pattern: string; regex_mode?: string; description?: string }) =>
    postJson<PatternConfig, Record<string, unknown>>("/api/patterns", data as Record<string, unknown>),

  updatePattern: (configId: string, data: { name?: string; pattern?: string; regex_mode?: string; description?: string }) =>
    requestJson<PatternConfig>(`/api/patterns/${encodeURIComponent(configId)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deletePattern: (configId: string) =>
    requestJson<{ ok: boolean }>(`/api/patterns/${encodeURIComponent(configId)}`, {
      method: "DELETE"
    }),

  importPatterns: (data: Record<string, unknown>) =>
    postJson<PatternImportResponse, Record<string, unknown>>("/api/patterns/import", data),

  exportPattern: (configId: string) =>
    requestJson<PatternConfig>(`/api/patterns/${encodeURIComponent(configId)}/export`),

  // ── 章节预览 ────────────────────────────────────────────────

  previewSplit: (request: SplitPreviewRequest) =>
    postJson<SplitPreviewResult, SplitPreviewRequest>("/api/chapters/preview-split", request),

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

  pickFile: async (title: string) => {
    const response = await postJson<BrowsePathResponse, { title: string }>(
      "/api/browse/file",
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

  saveProject: (
    projectSlug: string,
    request: {
      project_name: string;
      uploaded_file_ids?: string[];
      custom_output_directory_path?: string;
      migrate_existing_output?: boolean;
      summary_output_format?: "md" | "txt";
      summary_batch_size?: number;
      use_fine_grained_flow?: boolean;
    }
  ) =>
    requestJson<ProjectRecord>(`/api/projects/${encodeURIComponent(projectSlug)}`, {
      method: "PATCH",
      body: JSON.stringify(request)
    }),

  updateProjectName: (projectSlug: string, projectName: string) =>
    apiClient.saveProject(projectSlug, {
      project_name: projectName
    }),

  checkOutputMigration: (projectSlug: string, customOutputDirectoryPath: string) =>
    postJson<
      OutputMigrationInfo,
      { custom_output_directory_path?: string }
    >(`/api/projects/${encodeURIComponent(projectSlug)}/output-migration-check`, {
      custom_output_directory_path: customOutputDirectoryPath || undefined
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

  startSmallSummaryPreparation: (request: NovelSummaryRequest) =>
    postJson<TaskRecord, NovelSummaryRequest>("/api/tasks/novel/small-summary", {
      ...request,
      stop_after_small_summary: true
    }),

  precheckTriggerScan: (request: TriggerScanRequest) =>
    postJson<TriggerScanPrecheckResponse, TriggerScanRequest>(
      "/api/trigger-scan/precheck",
      request
    ),

  loadTriggerScanConfig: (projectSlug: string) =>
    requestJson<TriggerScanConfig>(
      `/api/trigger-scan/projects/${encodeURIComponent(projectSlug)}/config`
    ),

  saveTriggerScanConfig: (projectSlug: string, config: TriggerScanConfig) =>
    putJson<TriggerScanConfig, TriggerScanConfig>(
      `/api/trigger-scan/projects/${encodeURIComponent(projectSlug)}/config`,
      config
    ),

  startTriggerScan: (request: TriggerScanRequest) =>
    postJson<TaskRecord, TriggerScanRequest>("/api/tasks/trigger-scan", request),

  listTriggerScanReports: async (projectSlug: string) => {
    const response = await requestJson<TriggerScanReportListResponse>(
      `/api/trigger-scan/projects/${encodeURIComponent(projectSlug)}/reports`
    );
    return response.items;
  },

  getTriggerScanReport: (projectSlug: string, reportId: string) =>
    requestJson<ScanReport>(
      `/api/trigger-scan/projects/${encodeURIComponent(projectSlug)}/reports/${encodeURIComponent(reportId)}`
    ),

  deleteTriggerScanReport: (projectSlug: string, reportId: string) =>
    requestJson<{ ok: boolean; report_id: string }>(
      `/api/trigger-scan/projects/${encodeURIComponent(projectSlug)}/reports/${encodeURIComponent(reportId)}`,
      { method: "DELETE" }
    ),

  updateTriggerScanFinding: (
    projectSlug: string,
    reportId: string,
    findingId: string,
    request: { review_status?: TriggerReviewStatus; user_note?: string }
  ) =>
    requestJson<ScanFinding>(
      `/api/trigger-scan/projects/${encodeURIComponent(projectSlug)}/reports/${encodeURIComponent(reportId)}/findings/${encodeURIComponent(findingId)}`,
      { method: "PATCH", body: JSON.stringify(request) }
    ),

  getTriggerScanFindingContext: (
    projectSlug: string,
    reportId: string,
    findingId: string,
    before = 1,
    after = 1
  ) =>
    requestJson<TriggerScanContextResponse>(
      `/api/trigger-scan/projects/${encodeURIComponent(projectSlug)}/reports/${encodeURIComponent(reportId)}/findings/${encodeURIComponent(findingId)}/context?before=${before}&after=${after}`
    ),

  exportTriggerScanReport: (projectSlug: string, reportId: string, format: "md" | "json") =>
    postJson<TriggerScanExportResponse, { format: "md" | "json" }>(
      `/api/trigger-scan/projects/${encodeURIComponent(projectSlug)}/reports/${encodeURIComponent(reportId)}/export`,
      { format }
    ),

  startArticleSummary: (request: ArticleSummaryRequest) =>
    postJson<TaskRecord, ArticleSummaryRequest>("/api/tasks/article", request),

  startCustomSummary: (request: CustomSummaryRequest) =>
    postJson<TaskRecord, CustomSummaryRequest>("/api/tasks/custom", request),

  directSplit: (request: DirectSplitRequest) =>
    postJson<DirectSplitResult, DirectSplitRequest>("/api/splitter/direct", request),

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
