export type TaskStatus =
  | "pending"
  | "running"
  | "paused"
  | "canceling"
  | "cancelled"
  | "success"
  | "failed";

export type TaskType =
  | "novel_summary"
  | "article_summary"
  | "custom_summary"
  | "chapter_split"
  | "model_fetch";

export type WorkflowType =
  | "novel_summary"
  | "article_summary"
  | "custom_summary"
  | "chapter_split";

export interface ApiConfig {
  id: string;
  display_name: string;
  url: string;
  key: string;
  model: string;
  max_tokens: number;
  temperature: number;
  stream: boolean;
  timeout: number;
  max_retries: number;
  is_active: boolean;
  key_env_var: string;
  has_key?: boolean;
  has_env_key?: boolean;
}

export interface UserSettings {
  default_export_directory: string;
  minimum_output_characters: number;
}

export interface PromptTemplate {
  key: string;
  filename: string;
  text: string;
  default_text: string;
}

export type PromptRole = "system" | "user" | "assistant";
export type PromptMessageKind = "message" | "module";

export interface PromptMessage {
  id: string;
  kind?: PromptMessageKind;
  role: PromptRole;
  content: string;
  module_id?: string;
}

export interface PromptModule {
  id: string;
  name: string;
  description: string;
  content: string;
  default_content: string;
  messages?: PromptMessage[];
  default_messages?: PromptMessage[];
  is_dirty?: boolean;
}

export interface PromptNode {
  id: string;
  prompt_key: string;
  filename: string;
  title: string;
  description: string;
  variables: string[];
  messages: PromptMessage[];
  default_messages: PromptMessage[];
  is_dirty?: boolean;
}

export interface PromptWorkflow {
  id: string;
  title: string;
  description: string;
  empty_message: string;
  nodes: PromptNode[];
}

export interface WorkflowPromptConfig {
  version: number;
  source: "defaults" | "legacy" | "structured" | string;
  workflows: PromptWorkflow[];
  modules: PromptModule[];
}

export interface NovelWordCounts {
  small_summary_word_count: string;
  small_plot_word_count: string;
  small_char_word_count: string;
  big_plot_word_count: string;
  big_char_word_count: string;
  super_plot_p1_word_count: string;
  super_plot_p2_word_count: string;
  super_char_p1_word_count: string;
  super_char_p2_word_count: string;
  ultimate_plot_p1_word_count: string;
  ultimate_plot_p2_word_count: string;
  ultimate_char_p1_word_count: string;
  ultimate_char_p2_word_count: string;
}

export interface ArticleWordCounts {
  section: string;
  final: string;
}

export interface NovelSummaryRequest {
  source_folder_path: string;
  active_api_ids: string[];
  big_summary_batch_size: number;
  super_summary_threshold: number;
  ultimate_api_id: string;
  use_fine_grained_flow: boolean;
  word_counts?: NovelWordCounts;
  project_name?: string;
  project_slug?: string;
  uploaded_file_ids?: string[];
  custom_output_directory_path?: string;
}

export interface ArticleSummaryRequest {
  source_folder_path: string;
  selected_files: string[];
  output_subfolder: string;
  word_counts?: ArticleWordCounts;
  project_name?: string;
  project_slug?: string;
  uploaded_file_ids?: string[];
  custom_output_directory_path?: string;
}

export interface CustomSummaryRequest {
  selected_file_paths: string[];
  user_prompt: string;
  api_id: string;
  project_name?: string;
  project_slug?: string;
  uploaded_file_ids?: string[];
  custom_output_directory_path?: string;
}

export interface SplitterRequest {
  source_txt_file_path: string;
  output_directory_path: string;
  mode: "default" | "regex" | "title_list";
  chapters_per_file: number;
  custom_pattern: string;
  title_list: string[];
  handle_volumes: boolean;
  project_name?: string;
  project_slug?: string;
  uploaded_file_ids?: string[];
  custom_output_directory_path?: string;
}

export interface UploadedFileRef {
  id: string;
  project_slug: string;
  original_name: string;
  stored_name: string;
  path: string;
  size: number;
  uploaded_at: number;
  missing?: boolean;
}

export interface ProjectProgressStage {
  label: string;
  completed: number;
  total: number | null;
  status?: string;
}

export interface ProjectProgress {
  workflow_type: WorkflowType | string;
  summary: string;
  percent: number;
  stages: ProjectProgressStage[];
}

export interface ProjectRecord {
  project_name: string;
  project_slug: string;
  workflow_type: WorkflowType | string;
  default_output_directory: string;
  custom_output_directory: string;
  uploads: UploadedFileRef[];
  upload_count: number;
  latest_task_id: string;
  latest_task_status: TaskStatus | string;
  imported_from_path: string;
  progress: ProjectProgress;
  created_at: number;
  updated_at: number;
  warnings: string[];
}

export interface UploadTextFile {
  name: string;
  content: string;
}

export interface UploadResponse {
  project: ProjectRecord;
  items: UploadedFileRef[];
  workflow_output_directory: string;
}

export interface OutputMigrationInfo {
  requires_migration: boolean;
  file_count: number;
  previous_output_directory: string;
  new_output_directory: string;
  custom_output_directory: string;
}

export interface TaskEvent {
  task_id: string;
  event_type: "state" | "log" | "error" | "progress" | string;
  message: string;
  source_id: string;
  status: TaskStatus | string | null;
  progress_text: string | null;
  timestamp: number;
}

export interface TaskRecord {
  task_id: string;
  task_type: TaskType | string;
  status: TaskStatus;
  progress_text: string;
  created_at: number;
  updated_at: number;
  finished_at: number | null;
  result_summary: string | null;
  error: string | null;
  params_summary: Record<string, unknown>;
  events: TaskEvent[];
}

export interface ApiListResponse {
  items: ApiConfig[];
}

export interface PromptListResponse {
  items: PromptTemplate[];
  workflow_config: WorkflowPromptConfig;
}

export interface ModelListResponse {
  items: string[];
}

export interface TaskListResponse {
  items: TaskRecord[];
}

export interface ProjectListResponse {
  items: ProjectRecord[];
}

export interface DeleteProjectResponse {
  ok: boolean;
  project_slug: string;
}

export interface OpenDirectoryResponse {
  ok: boolean;
  path: string;
}

export interface BrowsePathResponse {
  path: string;
}

export interface ResolvePathResponse {
  path: string;
  resolved: boolean;
  is_directory: boolean;
}
