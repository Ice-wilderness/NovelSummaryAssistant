import { describe, expect, it } from "vitest";
import type { ScanEvent, ScanFinding, ScanReport } from "../../api/types";
import {
  emptyFilters,
  filterFindings,
  paginateFindings,
  totalFindingPages,
  visibleEvents
} from "./resultFilters";

function finding(id: string, overrides: Partial<ScanFinding> = {}): ScanFinding {
  return {
    finding_id: id,
    rule_id: "rule-1",
    rule_name: "规则一",
    chapter_file: "第1章.txt",
    chapter_title: "第一章",
    paragraph_ids: ["P001"],
    severity: 3,
    confidence: 0.7,
    is_main_plot: false,
    review_status: "unreviewed",
    verification_status: "verified",
    verification_note: "",
    user_note: "",
    spoiler_levels: {
      low: { description: "", skip_advice: "", evidence_quote: "" },
      standard: { description: "", skip_advice: "", evidence_quote: "" },
      detailed: { description: "", skip_advice: "", evidence_quote: "" }
    },
    ...overrides
  };
}

function event(id: string, findingIds: string[]): ScanEvent {
  return {
    event_id: id,
    rule_id: "rule-1",
    rule_name: "规则一",
    first_chapter: "第1章",
    related_chapters: ["第1章"],
    max_severity: 4,
    max_confidence: 0.9,
    is_main_plot: true,
    finding_ids: findingIds,
    event_summary: {
      low: "低",
      standard: "标准",
      detailed: "详细"
    }
  };
}

function report(findings: ScanFinding[], events: ScanEvent[]): ScanReport {
  return {
    report_id: "report",
    project_slug: "project",
    profile_id: "profile",
    profile_name: "档案",
    scan_mode: "precise",
    scan_range: { start: 1, end: null },
    scan_config: {
      scan_mode: "precise",
      scan_range: { start: 1, end: null },
      scan_api_ids: [],
      min_confidence: 0,
      keep_low_confidence: false,
      verification_enabled: false,
      verification_api_id: "",
      precise_chapter_batch_size: 5,
      verification_chapter_batch_size: 5,
      max_quote_chars: 80,
      generate_skip_advice: true,
      minimum_output_characters: 0
    },
    created_at: 1,
    completed_at: null,
    status: "completed",
    summary: {
      total_findings: findings.length,
      verified_findings: 0,
      pending_review: findings.length,
      rules_hit: []
    },
    findings,
    events,
    warnings: [],
    unscanned_chapters: [],
    failed_stage: "",
    profile_snapshot: null
  };
}

describe("trigger scan result filtering", () => {
  it("filters findings by high-risk and main-plot options", () => {
    const items = [
      finding("low-risk"),
      finding("main-risk", { severity: 4, confidence: 0.85, is_main_plot: true })
    ];

    const filtered = filterFindings(items, {
      ...emptyFilters,
      mainPlot: "main",
      highRiskOnly: true
    });

    expect(filtered.map((item) => item.finding_id)).toEqual(["main-risk"]);
  });

  it("filters related events when finding filters are active", () => {
    const findings = [
      finding("a", { rule_id: "rule-a" }),
      finding("b", { rule_id: "rule-b" })
    ];
    const filtered = filterFindings(findings, { ...emptyFilters, ruleId: "rule-b" });
    const visible = visibleEvents(report(findings, [event("event-a", ["a"]), event("event-b", ["b"])]), filtered, {
      ...emptyFilters,
      ruleId: "rule-b"
    });

    expect(visible.map((item) => item.event_id)).toEqual(["event-b"]);
  });

  it("paginates findings with a minimum of one page", () => {
    const findings = [finding("a"), finding("b"), finding("c")];

    expect(totalFindingPages(0, 20)).toBe(1);
    expect(totalFindingPages(21, 20)).toBe(2);
    expect(paginateFindings(findings, 2, 2).map((item) => item.finding_id)).toEqual(["c"]);
  });
});
