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

export interface ApiConfig {
  id: string;
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

export interface PromptTemplate {
  key: string;
  filename: string;
  text: string;
  default_text: string;
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
}

export interface ArticleSummaryRequest {
  source_folder_path: string;
  selected_files: string[];
  output_subfolder: string;
  word_counts?: ArticleWordCounts;
}

export interface CustomSummaryRequest {
  selected_file_paths: string[];
  user_prompt: string;
  api_id: string;
}

export interface SplitterRequest {
  source_txt_file_path: string;
  output_directory_path: string;
  mode: "default" | "regex" | "title_list";
  chapters_per_file: number;
  custom_pattern: string;
  title_list: string[];
  handle_volumes: boolean;
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
}

export interface ModelListResponse {
  items: string[];
}
