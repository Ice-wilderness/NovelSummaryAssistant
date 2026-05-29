import type {
  ProjectRecord,
  ScanFinding,
  ScanReport,
  SpoilerLevel
} from "../../api/types";

export function classNames(...values: Array<string | false | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function formatTime(timestamp?: number | null) {
  if (!timestamp) {
    return "暂无时间";
  }
  return new Date(timestamp * 1000).toLocaleString();
}

export function workflowLabel(project: ProjectRecord) {
  return project.workflow_type === "chapter_split" ? "章节分割" : "小说总结";
}

export function chapterNumber(path: string) {
  const name = path.split(/[\\/]/).pop() ?? path;
  const match = name.match(/第\s*0*(\d+)\s*[章回]/);
  return match ? Number.parseInt(match[1], 10) : null;
}

export function pathName(path: string) {
  return path.split(/[\\/]/).pop() ?? path;
}

export function isFinding(value: unknown): value is ScanFinding {
  return Boolean(
    value &&
      typeof value === "object" &&
      "finding_id" in value &&
      "rule_name" in value &&
      "chapter_file" in value
  );
}

export function spoilerText(finding: ScanFinding, level: SpoilerLevel) {
  const detail = finding.spoiler_levels[level] ?? finding.spoiler_levels.standard;
  return detail?.description || "";
}

export function skipAdvice(finding: ScanFinding, level: SpoilerLevel) {
  const detail = finding.spoiler_levels[level] ?? finding.spoiler_levels.standard;
  return detail?.skip_advice || "";
}

export function evidenceQuote(finding: ScanFinding) {
  return finding.spoiler_levels.detailed?.evidence_quote || "";
}

export function statusText(status: string) {
  switch (status) {
    case "running":
      return "运行中";
    case "paused":
      return "已暂停";
    case "canceling":
      return "取消中";
    case "cancelled":
      return "已取消";
    case "success":
      return "已完成";
    case "partial_failed":
      return "部分失败";
    case "failed":
      return "失败";
    case "interrupted":
      return "已中断";
    case "completed":
      return "已完成";
    default:
      return status || "暂无";
  }
}

export function reportStatusText(status: string, compatibilityStatus?: string) {
  if (status === "failed" && compatibilityStatus === "legacy_partial_failed") {
    return "历史部分失败";
  }
  switch (status) {
    case "completed":
      return "已完成";
    case "failed":
      return "失败";
    case "running":
      return "扫描中";
    case "cancelled":
      return "已取消";
    case "partial_failed":
      return "部分失败";
    default:
      return status || "未知";
  }
}

export function reportStatusClass(status: string, compatibilityStatus?: string) {
  if (status === "completed") {
    return "success";
  }
  if (status === "failed" && compatibilityStatus === "legacy_partial_failed") {
    return "partial_failed";
  }
  return status || "idle";
}

export function reportWarningMessages(report: ScanReport) {
  const messages = new Set<string>();
  (report.warnings || []).forEach((warning) => {
    if (warning.trim()) {
      messages.add(warning);
    }
  });
  (report.compatibility_warnings || []).forEach((warning) => {
    if (warning.trim()) {
      messages.add(warning);
    }
  });
  if (report.status === "partial_failed") {
    messages.add("本次扫描部分失败，已保留已生成的发现和事件。");
  }
  if (report.failed_stage) {
    messages.add(`失败阶段：${report.failed_stage}`);
  }
  if (report.unscanned_chapters?.length) {
    const preview = report.unscanned_chapters.slice(0, 5).join("、");
    const suffix = report.unscanned_chapters.length > 5 ? ` 等 ${report.unscanned_chapters.length} 章` : "";
    messages.add(`未扫描章节：${preview}${suffix}`);
  }
  const unverifiedCount = report.findings.filter((finding) => finding.verification_status === "unverified").length;
  if (unverifiedCount > 0) {
    messages.add(`${unverifiedCount} 条发现未完成二次验证，请结合上下文复核。`);
  }
  return Array.from(messages);
}

export function reviewStatusText(status: string) {
  const labelMap: Record<string, string> = {
    unreviewed: "未复核",
    confirmed: "已确认",
    false_positive: "误报"
  };
  return labelMap[status] || status || "暂无";
}
