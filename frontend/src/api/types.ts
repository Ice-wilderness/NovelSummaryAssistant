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
  | "small_summary_preparation"
  | "trigger_scan"
  | "article_summary"
  | "custom_summary"
  | "chapter_split"
  | "model_fetch";

export type WorkflowType =
  | "novel_summary"
  | "article_summary"
  | "custom_summary"
  | "chapter_split";

export type SummaryOutputFormat = "md" | "txt";

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
  summary_batch_size: number;
  summary_output_format: SummaryOutputFormat;
  big_summary_batch_size: number;
  super_summary_threshold: number;
  ultimate_api_id: string;
  use_fine_grained_flow: boolean;
  stop_after_small_summary?: boolean;
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
  custom_pattern: string;
  title_list: string[];
  handle_volumes: boolean;
  context?: "novel_summary" | "chapter_split";
  pattern_config_id?: string;
  project_name?: string;
  project_slug?: string;
  uploaded_file_ids?: string[];
  custom_output_directory_path?: string;
}

export type TriggerScanMode = "precise";
export type TriggerMatchingPolicy =
  | "explicit_only"
  | "explicit_or_strongly_implied"
  | "any_hint";
export type TriggerReviewStatus = "unreviewed" | "confirmed" | "false_positive";
export type SpoilerLevel = "low" | "standard" | "detailed";

export interface ScanRange {
  start: number;
  end?: number | null;
}

export interface TriggerScanConfig {
  scan_mode: TriggerScanMode;
  scan_range: ScanRange;
  scan_api_ids: string[];
  min_confidence: number;
  keep_low_confidence: boolean;
  verification_enabled: boolean;
  verification_api_id: string;
  precise_chapter_batch_size: number;
  verification_chapter_batch_size: number;
  max_quote_chars: number;
  generate_skip_advice: boolean;
  minimum_output_characters: number;
}

export interface TriggerScanRequest {
  project_slug: string;
  profile_id: string;
  scan_config: TriggerScanConfig;
  custom_output_directory_path?: string;
  resume_from_report_id?: string;
}

export interface TriggerRuleGroup {
  id: string;
  name: string;
  rules: string[];
}

export interface TriggerRule {
  id: string;
  name: string;
  group_id: string;
  description: string;
  matching_policy: TriggerMatchingPolicy;
  severity_threshold: number;
  enabled: boolean;
  examples: string[];
  negative_examples: string[];
}

export interface TriggerProfile {
  id: string;
  name: string;
  description: string;
  created_at: number;
  updated_at: number;
  rule_groups: TriggerRuleGroup[];
  rules: TriggerRule[];
}

export interface TriggerProfileListResponse {
  items: TriggerProfile[];
}

export interface TriggerScanPrecheckResponse {
  ready: boolean;
  errors: string[];
  warnings: string[];
  decisions: string[];
  chapter_count: number;
  selected_chapter_count: number;
  pending_chapter_count: number;
  completed_chapter_count: number;
  chapter_files: string[];
  selected_chapter_files: string[];
  scan_config: TriggerScanConfig;
}

export interface TriggerScanReportHistoryItem {
  report_id: string;
  project_slug: string;
  profile_name: string;
  scan_mode: TriggerScanMode | string;
  scan_range: ScanRange;
  status: string;
  created_at: number;
  completed_at: number | null;
  finding_count: number;
}

export interface TriggerScanReportListResponse {
  items: TriggerScanReportHistoryItem[];
}

export interface SpoilerDescription {
  description: string;
  skip_advice: string;
  evidence_quote: string;
}

export interface SpoilerLevels {
  low: SpoilerDescription;
  standard: SpoilerDescription;
  detailed: SpoilerDescription;
}

export interface ScanFinding {
  finding_id: string;
  rule_id: string;
  rule_name: string;
  chapter_file: string;
  chapter_title: string;
  paragraph_ids: string[];
  severity: number;
  confidence: number;
  is_main_plot: boolean;
  review_status: TriggerReviewStatus | string;
  user_note: string;
  spoiler_levels: SpoilerLevels;
}

export interface ScanEvent {
  event_id: string;
  rule_id: string;
  rule_name: string;
  first_chapter: string;
  related_chapters: string[];
  max_severity: number;
  max_confidence: number;
  is_main_plot: boolean;
  finding_ids: string[];
  event_summary: Record<SpoilerLevel, string>;
}

export interface ScanReportSummary {
  total_findings: number;
  verified_findings: number;
  pending_review: number;
  rules_hit: Array<{
    rule_id: string;
    count: number;
    max_severity: number;
  }>;
}

export interface ScanReport {
  report_id: string;
  project_slug: string;
  profile_id: string;
  profile_name: string;
  scan_mode: TriggerScanMode | string;
  scan_range: ScanRange;
  scan_config: TriggerScanConfig;
  created_at: number;
  completed_at: number | null;
  status: string;
  summary: ScanReportSummary;
  events: ScanEvent[];
  findings: ScanFinding[];
  profile_snapshot: TriggerProfile | Record<string, unknown> | null;
}

export interface TriggerScanExportResponse {
  path: string;
  format: string;
}

export interface TriggerScanContextParagraph {
  id: string;
  text: string;
  line_number: number;
  matched: boolean;
}

export interface TriggerScanContextResponse {
  ok: boolean;
  warning?: string;
  chapter_file?: string;
  chapter_title?: string;
  matched_paragraph_ids?: string[];
  missing_paragraph_ids?: string[];
  paragraphs?: TriggerScanContextParagraph[];
  text?: string;
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
  summary_batch_size: number;
  summary_output_format: SummaryOutputFormat;
  requires_granularity_migration: boolean;
  legacy_grouped_file_count: number;
  granularity_migration_backup_path: string;
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

export interface GranularityMigrationInfo {
  requires_migration: boolean;
  inferred_summary_batch_size: number;
  grouped_file_count: number;
  grouped_files: Array<{
    name: string;
    path: string;
    chapter_count: number;
    reasons: string[];
  }>;
  summary_batch_size: number;
  project_slug: string;
}

export interface GranularityMigrationResult {
  project: ProjectRecord;
  migration: {
    requires_migration: boolean;
    migrated: boolean;
    generated_file_count: number;
    backup_path: string;
    summary_batch_size: number;
  };
}

export interface TaskEvent {
  task_id: string;
  event_type: "state" | "log" | "error" | "progress" | string;
  message: string;
  source_id: string;
  status: TaskStatus | string | null;
  progress_text: string | null;
  data: Record<string, unknown>;
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

// ── 正则配置模块 ──────────────────────────────────────────────

export type PatternRegexMode = "raw" | "simple";

export interface PatternConfig {
  id: string;
  name: string;
  regex_mode: PatternRegexMode;
  pattern: string;
  description: string;
  is_preset: boolean;
  created_at: number;
  updated_at: number;
}

export interface PatternConfigListResponse {
  items: PatternConfig[];
}

export interface PatternImportResponse {
  imported_count: number;
  items: PatternConfig[];
}

// ── 章节预览 ──────────────────────────────────────────────────

export interface ChapterPreviewItem {
  index: number;
  title: string;
  line_number: number;
  matched?: boolean;
}

export interface SplitPreviewResult {
  chapter_count: number;
  chapters: ChapterPreviewItem[];
}

export interface SplitPreviewRequest {
  file_content: string;
  mode: "default" | "regex" | "title_list";
  pattern_config_id?: string;
  title_list?: string[];
  handle_volumes?: boolean;
  uploaded_file_ids?: string[];
  project_slug?: string;
}
