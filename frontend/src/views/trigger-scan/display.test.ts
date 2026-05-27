import { describe, expect, it } from "vitest";
import type { ScanFinding, ScanReport } from "../../api/types";
import {
  reportStatusText,
  reportWarningMessages,
  skipAdvice,
  spoilerText,
  statusText
} from "./display";

function finding(overrides: Partial<ScanFinding> = {}): ScanFinding {
  return {
    finding_id: "finding-1",
    rule_id: "rule-1",
    rule_name: "规则一",
    chapter_file: "第1章.txt",
    chapter_title: "第一章",
    paragraph_ids: ["P001"],
    severity: 4,
    confidence: 0.9,
    is_main_plot: true,
    review_status: "unreviewed",
    verification_status: "verified",
    verification_note: "",
    user_note: "",
    spoiler_levels: {
      low: { description: "低剧透", skip_advice: "", evidence_quote: "" },
      standard: { description: "标准剧透", skip_advice: "跳读建议", evidence_quote: "" },
      detailed: { description: "详细剧透", skip_advice: "详细建议", evidence_quote: "证据" }
    },
    ...overrides
  };
}

function report(overrides: Partial<ScanReport> = {}): ScanReport {
  return {
    report_id: "report-1",
    project_slug: "project",
    profile_id: "profile",
    profile_name: "档案",
    scan_mode: "precise",
    scan_range: { start: 1, end: null },
    scan_config: {
      scan_mode: "precise",
      scan_range: { start: 1, end: null },
      scan_api_ids: ["api"],
      min_confidence: 0.4,
      keep_low_confidence: false,
      verification_enabled: true,
      verification_api_id: "api",
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
      total_findings: 1,
      verified_findings: 0,
      pending_review: 1,
      rules_hit: []
    },
    events: [],
    findings: [finding()],
    warnings: [],
    unscanned_chapters: [],
    failed_stage: "",
    profile_snapshot: null,
    ...overrides
  };
}

describe("trigger scan display helpers", () => {
  it("keeps terminal status labels distinct", () => {
    expect(statusText("cancelled")).toBe("已取消");
    expect(statusText("partial_failed")).toBe("部分失败");
    expect(statusText("interrupted")).toBe("已中断");
    expect(reportStatusText("partial_failed")).toBe("部分失败");
  });

  it("adds report warnings for partial and unverified results", () => {
    const messages = reportWarningMessages(
      report({
        status: "partial_failed",
        failed_stage: "verification",
        findings: [finding({ verification_status: "unverified" })],
        unscanned_chapters: ["第1章", "第2章", "第3章", "第4章", "第5章", "第6章"]
      })
    );

    expect(messages).toContain("本次扫描部分失败，已保留已生成的发现和事件。");
    expect(messages).toContain("失败阶段：verification");
    expect(messages).toContain("1 条发现未完成二次验证，请结合上下文复核。");
    expect(messages.some((message) => message.includes("等 6 章"))).toBe(true);
  });

  it("falls back to standard spoiler text when a level is missing", () => {
    const item = finding({
      spoiler_levels: {
        low: undefined as unknown as ScanFinding["spoiler_levels"]["low"],
        standard: { description: "标准", skip_advice: "标准建议", evidence_quote: "" },
        detailed: { description: "详细", skip_advice: "详细建议", evidence_quote: "证据" }
      }
    });

    expect(spoilerText(item, "low")).toBe("标准");
    expect(skipAdvice(item, "low")).toBe("标准建议");
  });
});
