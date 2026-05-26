import type { TaskRecord } from "../api/types";

type SummaryPartialKind = "article" | "custom";

interface FailedUnit {
  filename?: string;
  source_file?: string;
  error?: string;
}

interface SummaryPartialDetails {
  title: string;
  warnings: string[];
  failedUnits: FailedUnit[];
  retainedResult: string;
}

function stringValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

function failedUnitsFrom(value: unknown): FailedUnit[] {
  return Array.isArray(value) ? value.filter((item) => item && typeof item === "object") as FailedUnit[] : [];
}

export function getSummaryPartialDetails(
  task: TaskRecord | null | undefined,
  kind: SummaryPartialKind
): SummaryPartialDetails | null {
  if (!task || task.status !== "partial_failed") {
    return null;
  }
  const isArticle = kind === "article";
  const failedUnits = failedUnitsFrom(
    isArticle ? task.result_data.failed_sections : task.result_data.failed_source_files
  );
  const fallbackWarning = isArticle
    ? "文章总结已保留可用结果，但部分段落生成失败，最终总结可能不完整。"
    : "自定义总结已保留可用结果，但部分参考材料读取失败，结果可能不完整。";
  const retainedResult = isArticle
    ? stringValue(task.result_data.final_output_path) || task.result_summary || ""
    : stringValue(task.result_data.output_text) || task.result_summary || "";

  return {
    title: isArticle ? "文章总结部分结果" : "自定义总结部分结果",
    warnings: task.warnings.length > 0 ? task.warnings : [fallbackWarning],
    failedUnits,
    retainedResult
  };
}

function failedUnitLabel(unit: FailedUnit) {
  const filename = unit.filename || unit.source_file || "未知输入";
  return unit.error ? `${filename}：${unit.error}` : filename;
}

export function SummaryPartialNotice({
  task,
  kind
}: {
  task: TaskRecord | null | undefined;
  kind: SummaryPartialKind;
}) {
  const details = getSummaryPartialDetails(task, kind);
  if (!details) {
    return null;
  }

  return (
    <section className="report-warning-panel" aria-label="总结结果警告">
      <strong>{details.title}</strong>
      {details.warnings.map((warning) => (
        <span key={warning}>{warning}</span>
      ))}
      {details.failedUnits.length > 0 ? (
        <ul>
          {details.failedUnits.map((unit, index) => (
            <li key={`${unit.filename || unit.source_file || "unit"}-${index}`}>
              {failedUnitLabel(unit)}
            </li>
          ))}
        </ul>
      ) : (
        <span>部分输入失败，未返回详细列表。</span>
      )}
      {details.retainedResult ? <span>可用结果：{details.retainedResult}</span> : null}
    </section>
  );
}
