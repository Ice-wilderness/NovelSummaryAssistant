import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import type {
  ProjectRecord,
  ScanReport,
  TriggerProfile,
  TriggerScanConfig,
  TriggerScanReportHistoryItem
} from "../api/types";
import { AppStateProvider } from "../state/AppState";
import { TriggerScanPage } from "./TriggerScanPage";

const scanConfig: TriggerScanConfig = {
  scan_mode: "precise",
  scan_range: { start: 1, end: null },
  scan_api_ids: [],
  min_confidence: 0.45,
  keep_low_confidence: false,
  verification_enabled: true,
  verification_api_id: "",
  precise_chapter_batch_size: 5,
  verification_chapter_batch_size: 5,
  max_quote_chars: 80,
  generate_skip_advice: true,
  minimum_output_characters: 0
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

describe("TriggerScanPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not request a stale report id after switching scan projects", async () => {
    const firstProject = makeProject("project-a", "项目 A");
    const secondProject = makeProject("project-b", "项目 B");
    const firstReport = makeHistory("project-a", "report-a");
    const secondReport = makeHistory("project-b", "report-b");
    const getReport = vi
      .spyOn(apiClient, "getTriggerScanReport")
      .mockImplementation(async (projectSlug, reportId) => makeReport(projectSlug, reportId));

    vi.spyOn(apiClient, "listProjects").mockResolvedValue([firstProject, secondProject]);
    vi.spyOn(apiClient, "listTriggerProfiles").mockResolvedValue([profile]);
    vi.spyOn(apiClient, "loadTriggerScanConfig").mockResolvedValue(scanConfig);
    vi.spyOn(apiClient, "listTriggerScanReports").mockImplementation(async (projectSlug) =>
      projectSlug === "project-a" ? [firstReport] : [secondReport]
    );

    render(
      <AppStateProvider>
        <TriggerScanPage />
      </AppStateProvider>
    );

    await waitFor(() => {
      expect(getReport).toHaveBeenCalledWith("project-a", "report-a");
    });

    const projectSelect = screen.getAllByRole("combobox")[0];
    expect(projectSelect).toHaveValue("project-a");

    fireEvent.change(projectSelect, {
      target: { value: "project-b" }
    });

    await waitFor(() => {
      expect(getReport).toHaveBeenCalledWith("project-b", "report-b");
    });

    expect(getReport).not.toHaveBeenCalledWith("project-b", "report-a");
  });
});

function makeProject(project_slug: string, project_name: string): ProjectRecord {
  return {
    project_name,
    project_slug,
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
}

function makeHistory(
  project_slug: string,
  report_id: string
): TriggerScanReportHistoryItem {
  return {
    report_id,
    project_slug,
    profile_name: "雷点档案",
    scan_mode: "precise",
    scan_range: { start: 1, end: null },
    status: "completed",
    created_at: 1,
    completed_at: 2,
    finding_count: 0
  };
}

function makeReport(project_slug: string, report_id: string): ScanReport {
  return {
    report_id,
    project_slug,
    profile_id: profile.id,
    profile_name: profile.name,
    scan_mode: "precise",
    scan_range: { start: 1, end: null },
    scan_config: scanConfig,
    created_at: 1,
    completed_at: 2,
    status: "completed",
    summary: {
      total_findings: 0,
      verified_findings: 0,
      pending_review: 0,
      rules_hit: []
    },
    events: [],
    findings: [],
    warnings: [],
    unscanned_chapters: [],
    failed_stage: "",
    profile_snapshot: profile
  };
}
