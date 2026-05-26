import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type {
  ApiConfig,
  ProjectRecord,
  TriggerProfile,
  TriggerScanPrecheckResponse
} from "../../api/types";
import { ScanConfigTab } from "./ScanConfigTab";

const api: ApiConfig = {
  id: "api-1",
  display_name: "API One",
  url: "http://example.test",
  key: "",
  model: "model",
  max_tokens: 1000,
  temperature: 0.2,
  stream: false,
  timeout: 30,
  max_retries: 3,
  is_active: true,
  key_env_var: ""
};

const project: ProjectRecord = {
  project_name: "项目一",
  project_slug: "project-1",
  workflow_type: "novel_summary",
  default_output_directory: "",
  custom_output_directory: "",
  summary_batch_size: 5,
  summary_output_format: "md",
  use_fine_grained_flow: false,
  requires_granularity_migration: false,
  legacy_grouped_file_count: 0,
  granularity_migration_backup_path: "",
  uploads: [],
  upload_count: 0,
  latest_task_id: "",
  latest_task_status: "success",
  imported_from_path: "",
  progress: {
    workflow_type: "novel_summary",
    summary: "",
    percent: 0,
    stages: []
  },
  created_at: 1,
  updated_at: 2,
  warnings: []
};

const profile: TriggerProfile = {
  id: "profile-1",
  name: "雷点档案",
  description: "",
  created_at: 1,
  updated_at: 2,
  rule_groups: [],
  rules: []
};

function precheck(overrides: Partial<TriggerScanPrecheckResponse> = {}): TriggerScanPrecheckResponse {
  return {
    ready: true,
    errors: [],
    warnings: [],
    decisions: [],
    chapter_count: 10,
    selected_chapter_count: 10,
    pending_chapter_count: 10,
    completed_chapter_count: 0,
    chapter_files: [],
    selected_chapter_files: [],
    scan_config: {
      scan_mode: "precise",
      scan_range: { start: 1, end: null },
      scan_api_ids: ["api-1"],
      min_confidence: 0.45,
      keep_low_confidence: false,
      verification_enabled: true,
      verification_api_id: "api-1",
      precise_chapter_batch_size: 5,
      verification_chapter_batch_size: 5,
      max_quote_chars: 80,
      generate_skip_advice: true,
      minimum_output_characters: 0
    },
    ...overrides
  };
}

function renderScanConfigTab(overrides: Partial<Parameters<typeof ScanConfigTab>[0]> = {}) {
  const props: Parameters<typeof ScanConfigTab>[0] = {
    activeApis: [api],
    canPrecheck: true,
    canStart: true,
    generateSkipAdvice: true,
    keepLowConfidence: false,
    latestTriggerTask: null,
    liveFindings: [],
    maxQuoteChars: 80,
    minConfidence: 0.45,
    minimumOutputCharacters: 0,
    onCancelDecision: vi.fn(),
    onControlTriggerTask: vi.fn(),
    onGenerateSkipAdviceChange: vi.fn(),
    onKeepLowConfidenceChange: vi.fn(),
    onLoadProjects: vi.fn(),
    onMaxQuoteCharsChange: vi.fn(),
    onMinConfidenceChange: vi.fn(),
    onMinimumOutputCharactersChange: vi.fn(),
    onPreciseChapterBatchSizeChange: vi.fn(),
    onRangeEndChange: vi.fn(),
    onRangeStartChange: vi.fn(),
    onResumeReportChange: vi.fn(),
    onRunPrecheck: vi.fn(),
    onSaveConfig: vi.fn(),
    onScanApiToggle: vi.fn(),
    onSelectedProfileChange: vi.fn(),
    onSelectedProjectChange: vi.fn(),
    onStartScan: vi.fn(),
    onVerificationApiChange: vi.fn(),
    onVerificationChapterBatchSizeChange: vi.fn(),
    onVerificationEnabledChange: vi.fn(),
    preciseChapterBatchSize: 5,
    precheck: null,
    profiles: [profile],
    rangeEnd: "",
    rangeStart: 1,
    reports: [],
    resumeReportId: "",
    scanApiIds: ["api-1"],
    scanCurrentStage: "",
    scanProjects: [project],
    scanStages: [],
    selectedProfileId: profile.id,
    selectedProjectSlug: project.project_slug,
    triggerEvents: [],
    verificationApiId: api.id,
    verificationChapterBatchSize: 5,
    verificationEnabled: true,
    ...overrides
  };
  render(<ScanConfigTab {...props} />);
  return props;
}

describe("ScanConfigTab", () => {
  it("delegates scan API selection changes", () => {
    const props = renderScanConfigTab({ scanApiIds: [] });

    fireEvent.click(screen.getByLabelText("API One"));

    expect(props.onScanApiToggle).toHaveBeenCalledWith("api-1", true);
  });

  it("keeps start disabled when the page cannot start", () => {
    renderScanConfigTab({ canStart: false });

    expect(screen.getByRole("button", { name: /开始扫描/ })).toBeDisabled();
  });

  it("shows resumed progress counts from precheck", () => {
    renderScanConfigTab({
      precheck: precheck({
        pending_chapter_count: 3,
        selected_chapter_count: 10,
        completed_chapter_count: 7
      })
    });

    expect(screen.getByText("3 章待扫描（已完成 7 章）")).toBeInTheDocument();
  });
});
