import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ScanEvent, ScanFinding, ScanReport, TriggerScanReportHistoryItem } from "../../api/types";
import { ResultsTab } from "./ResultsTab";
import { emptyFilters } from "./resultFilters";

function finding(): ScanFinding {
  return {
    finding_id: "finding-1",
    rule_id: "rule-1",
    rule_name: "规则一",
    chapter_file: "chapters/chapter-001.txt",
    chapter_title: "第一章",
    paragraph_ids: ["P1"],
    severity: 4,
    confidence: 0.91,
    is_main_plot: true,
    review_status: "unreviewed",
    user_note: "",
    spoiler_levels: {
      low: {
        description: "低剧透描述",
        evidence_quote: "",
        skip_advice: ""
      },
      standard: {
        description: "标准描述",
        evidence_quote: "",
        skip_advice: "跳过建议"
      },
      detailed: {
        description: "详细描述",
        evidence_quote: "证据句",
        skip_advice: "跳过建议"
      }
    }
  };
}

function event(item: ScanFinding): ScanEvent {
  return {
    event_id: "event-1",
    rule_id: item.rule_id,
    rule_name: item.rule_name,
    first_chapter: item.chapter_title,
    related_chapters: [item.chapter_title],
    max_severity: item.severity,
    max_confidence: item.confidence,
    is_main_plot: item.is_main_plot,
    finding_ids: [item.finding_id],
    event_summary: {
      low: "低剧透事件",
      standard: "标准事件",
      detailed: "详细事件"
    }
  };
}

function report(item: ScanFinding, scanEvent: ScanEvent): ScanReport {
  return {
    report_id: "report-1",
    project_slug: "project-1",
    profile_id: "profile-1",
    profile_name: "默认档案",
    scan_mode: "precise",
    scan_range: { start: 1, end: null },
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
    created_at: 1,
    completed_at: 2,
    status: "partial_failed",
    summary: {
      total_findings: 1,
      verified_findings: 0,
      pending_review: 1,
      rules_hit: [{ rule_id: item.rule_id, count: 1, max_severity: item.severity }]
    },
    events: [scanEvent],
    findings: [item],
    warnings: [],
    unscanned_chapters: [],
    failed_stage: "",
    compatibility_status: "",
    compatibility_warnings: [],
    profile_snapshot: null
  };
}

function historyItem(item: ScanReport): TriggerScanReportHistoryItem {
  return {
    report_id: item.report_id,
    project_slug: item.project_slug,
    profile_name: item.profile_name,
    scan_mode: item.scan_mode,
    scan_range: item.scan_range,
    status: item.status,
    created_at: item.created_at,
    completed_at: item.completed_at,
    finding_count: item.findings.length,
    compatibility_status: item.compatibility_status,
    compatibility_warnings: item.compatibility_warnings
  };
}

function renderResultsTab(overrides: Partial<Parameters<typeof ResultsTab>[0]> = {}) {
  const item = finding();
  const scanEvent = event(item);
  const scanReport = report(item, scanEvent);
  const props: Parameters<typeof ResultsTab>[0] = {
    expandedEventIds: new Set(),
    filteredFindings: [item],
    filters: emptyFilters,
    findingPage: 1,
    globalSpoiler: "standard",
    itemSpoilers: {},
    notes: {},
    onDeleteReport: vi.fn(),
    onExportReport: vi.fn(),
    onOpenContext: vi.fn(),
    onRefreshReports: vi.fn(),
    onSetExpandedEventIds: vi.fn(),
    onSetFilters: vi.fn(),
    onSetFindingPage: vi.fn(),
    onSetGlobalSpoiler: vi.fn(),
    onSetItemSpoilers: vi.fn(),
    onSetNotes: vi.fn(),
    onSetPageSize: vi.fn(),
    onSetResultView: vi.fn(),
    onSetSelectedReportId: vi.fn(),
    onUpdateFinding: vi.fn(),
    pageSize: 10,
    pagedFindings: [item],
    report: scanReport,
    reportWarnings: ["部分章节未完成扫描"],
    reports: [historyItem(scanReport)],
    resultView: "findings",
    ruleOptions: [{ label: item.rule_name, value: item.rule_id }],
    selectedReportId: scanReport.report_id,
    totalPages: 1,
    visibleEvents: [scanEvent],
    ...overrides
  };
  render(<ResultsTab {...props} />);
  return props;
}

describe("ResultsTab", () => {
  it("shows report warnings and summary status", () => {
    renderResultsTab();

    expect(screen.getByText("部分章节未完成扫描")).toBeInTheDocument();
    expect(screen.getAllByText("部分失败").length).toBeGreaterThan(0);
  });

  it("delegates review status changes from finding actions", () => {
    const props = renderResultsTab();

    fireEvent.click(screen.getByRole("button", { name: /确认/ }));

    expect(props.onUpdateFinding).toHaveBeenCalledWith(
      expect.objectContaining({ finding_id: "finding-1" }),
      { review_status: "confirmed" }
    );
  });

  it("labels legacy-compatible reports without hiding findings", () => {
    const item = finding();
    const scanEvent = event(item);
    const legacyReport = {
      ...report(item, scanEvent),
      status: "failed",
      compatibility_status: "legacy_partial_failed",
      compatibility_warnings: ["历史兼容报告：旧版扫描失败后保留了部分结果，不能视为完整成功报告。"]
    };

    renderResultsTab({
      report: legacyReport,
      reportWarnings: legacyReport.compatibility_warnings,
      reports: [historyItem(legacyReport)]
    });

    expect(screen.getAllByText("历史部分失败").length).toBeGreaterThan(0);
    expect(screen.getByText("历史兼容报告：旧版扫描失败后保留了部分结果，不能视为完整成功报告。")).toBeInTheDocument();
    expect(screen.getAllByText("规则一").length).toBeGreaterThan(0);
  });

  it("shows completed and warning-bearing report states", () => {
    const item = finding();
    const scanEvent = event(item);
    const completedReport = {
      ...report(item, scanEvent),
      status: "completed",
      warnings: ["报告包含人工复核提示"]
    };

    renderResultsTab({
      report: completedReport,
      reportWarnings: completedReport.warnings,
      reports: [historyItem(completedReport)]
    });

    expect(screen.getAllByText("已完成").length).toBeGreaterThan(0);
    expect(screen.getByText("报告包含人工复核提示")).toBeInTheDocument();
    expect(screen.getByText("标准描述")).toBeInTheDocument();
  });
});
