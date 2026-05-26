import type {
  ScanEvent,
  ScanFinding,
  ScanReport,
  TriggerReviewStatus
} from "../../api/types";

export interface ResultFilters {
  ruleId: string;
  reviewStatus: string;
  minSeverity: number;
  minConfidence: number;
  chapterText: string;
  mainPlot: "all" | "main" | "side";
  highRiskOnly: boolean;
}

export const emptyFilters: ResultFilters = {
  ruleId: "",
  reviewStatus: "",
  minSeverity: 1,
  minConfidence: 0,
  chapterText: "",
  mainPlot: "all",
  highRiskOnly: false
};

export const reviewOptions: Array<{ label: string; value: TriggerReviewStatus | "" }> = [
  { label: "全部", value: "" },
  { label: "未复核", value: "unreviewed" },
  { label: "确认", value: "confirmed" },
  { label: "误报", value: "false_positive" }
];

export function buildRuleOptions(findings: ScanFinding[]) {
  const rules = new Map<string, string>();
  findings.forEach((finding) => {
    rules.set(finding.rule_id, finding.rule_name);
  });
  return Array.from(rules.entries()).map(([value, label]) => ({ value, label }));
}

export function filterFindings(findings: ScanFinding[], filters: ResultFilters) {
  const chapterFilter = filters.chapterText.trim().toLocaleLowerCase();
  return findings.filter((finding) => {
    if (filters.ruleId && finding.rule_id !== filters.ruleId) {
      return false;
    }
    if (filters.reviewStatus && finding.review_status !== filters.reviewStatus) {
      return false;
    }
    if (finding.severity < filters.minSeverity) {
      return false;
    }
    if (finding.confidence < filters.minConfidence) {
      return false;
    }
    if (chapterFilter) {
      const chapterText = `${finding.chapter_file} ${finding.chapter_title}`.toLocaleLowerCase();
      if (!chapterText.includes(chapterFilter)) {
        return false;
      }
    }
    if (filters.mainPlot === "main" && !finding.is_main_plot) {
      return false;
    }
    if (filters.mainPlot === "side" && finding.is_main_plot) {
      return false;
    }
    if (filters.highRiskOnly && finding.severity < 4 && finding.confidence < 0.8) {
      return false;
    }
    return true;
  });
}

export function paginateFindings(findings: ScanFinding[], page: number, pageSize: number) {
  return findings.slice((page - 1) * pageSize, page * pageSize);
}

export function totalFindingPages(totalFindings: number, pageSize: number) {
  return Math.max(1, Math.ceil(totalFindings / pageSize));
}

export function hasActiveFilters(filters: ResultFilters) {
  return Boolean(
    filters.ruleId ||
      filters.reviewStatus ||
      filters.minSeverity > 1 ||
      filters.minConfidence > 0 ||
      filters.chapterText.trim() ||
      filters.mainPlot !== "all" ||
      filters.highRiskOnly
  );
}

export function visibleEvents(report: ScanReport, filteredFindings: ScanFinding[], filters: ResultFilters): ScanEvent[] {
  const visibleFindingIds = new Set(filteredFindings.map((finding) => finding.finding_id));
  if (!hasActiveFilters(filters)) {
    return report.events;
  }
  return report.events.filter((event) =>
    event.finding_ids.some((findingId) => visibleFindingIds.has(findingId))
  );
}
