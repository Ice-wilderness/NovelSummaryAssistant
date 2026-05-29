import {
  Check,
  Eye,
  FileDown,
  RefreshCw,
  Save,
  ShieldAlert,
  Trash2,
  X
} from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import type {
  ScanEvent,
  ScanFinding,
  ScanReport,
  SpoilerLevel,
  TriggerReviewStatus,
  TriggerScanReportHistoryItem
} from "../../api/types";
import { IconButton } from "../../components/common/IconButton";
import {
  NumberInput,
  SelectField,
  TextInput,
  ToggleSwitch
} from "../../components/forms/FormControls";
import {
  classNames,
  evidenceQuote,
  formatTime,
  pathName,
  reportStatusClass,
  reportStatusText,
  reviewStatusText,
  skipAdvice,
  spoilerText
} from "./display";
import { spoilerOptions, type ResultView } from "./options";
import { emptyFilters, reviewOptions, type ResultFilters } from "./resultFilters";

interface ResultsTabProps {
  expandedEventIds: Set<string>;
  filteredFindings: ScanFinding[];
  filters: ResultFilters;
  findingPage: number;
  globalSpoiler: SpoilerLevel;
  itemSpoilers: Record<string, SpoilerLevel>;
  notes: Record<string, string>;
  pageSize: number;
  pagedFindings: ScanFinding[];
  report: ScanReport | null;
  reportWarnings: string[];
  reports: TriggerScanReportHistoryItem[];
  resultView: ResultView;
  ruleOptions: Array<{ label: string; value: string }>;
  selectedReportId: string;
  totalPages: number;
  visibleEvents: ScanEvent[];
  onDeleteReport: (reportId?: string) => void;
  onExportReport: (format: "md" | "json") => void;
  onOpenContext: (finding: ScanFinding) => void;
  onRefreshReports: () => void;
  onSetExpandedEventIds: Dispatch<SetStateAction<Set<string>>>;
  onSetFilters: Dispatch<SetStateAction<ResultFilters>>;
  onSetFindingPage: Dispatch<SetStateAction<number>>;
  onSetGlobalSpoiler: (level: SpoilerLevel) => void;
  onSetItemSpoilers: Dispatch<SetStateAction<Record<string, SpoilerLevel>>>;
  onSetNotes: Dispatch<SetStateAction<Record<string, string>>>;
  onSetPageSize: (pageSize: number) => void;
  onSetResultView: (view: ResultView) => void;
  onSetSelectedReportId: (reportId: string) => void;
  onUpdateFinding: (
    finding: ScanFinding,
    payload: { review_status?: TriggerReviewStatus; user_note?: string }
  ) => void;
}

export function ResultsTab({
  expandedEventIds,
  filteredFindings,
  filters,
  findingPage,
  globalSpoiler,
  itemSpoilers,
  notes,
  pageSize,
  pagedFindings,
  report,
  reportWarnings,
  reports,
  resultView,
  ruleOptions,
  selectedReportId,
  totalPages,
  visibleEvents,
  onDeleteReport,
  onExportReport,
  onOpenContext,
  onRefreshReports,
  onSetExpandedEventIds,
  onSetFilters,
  onSetFindingPage,
  onSetGlobalSpoiler,
  onSetItemSpoilers,
  onSetNotes,
  onSetPageSize,
  onSetResultView,
  onSetSelectedReportId,
  onUpdateFinding
}: ResultsTabProps) {
  const getFindingSpoiler = (findingId: string, eventId?: string): SpoilerLevel =>
    itemSpoilers[findingId] ?? (eventId ? itemSpoilers[eventId] : undefined) ?? globalSpoiler;

  const setEventSpoilerLevel = (eventId: string, findingIds: string[], level: SpoilerLevel) => {
    onSetItemSpoilers((current) => {
      const next = { ...current, [eventId]: level };
      for (const findingId of findingIds) {
        next[findingId] = level;
      }
      return next;
    });
  };

  const renderFindingBody = (finding: ScanFinding, spoilerLevel: SpoilerLevel) => {
    const evidence = spoilerLevel === "detailed" ? evidenceQuote(finding) : "";
    const advice = skipAdvice(finding, spoilerLevel);
    return (
      <>
        <span>{spoilerText(finding, spoilerLevel)}</span>
        {evidence ? <small>证据：{evidence}</small> : null}
        {advice ? <small>建议：{advice}</small> : null}
      </>
    );
  };

  const renderFindingActions = (finding: ScanFinding) => {
    const selectedSpoiler = itemSpoilers[finding.finding_id] ?? globalSpoiler;
    const noteValue = notes[finding.finding_id] ?? finding.user_note;
    return (
      <div className="finding-actions">
        <div className="finding-actions__left">
          <input
            className="text-control finding-actions__note"
            onChange={(event) =>
              onSetNotes((current) => ({ ...current, [finding.finding_id]: event.target.value }))
            }
            placeholder="备注"
            value={noteValue}
          />
          <button
            className="secondary-command secondary-command--compact"
            onClick={() => onUpdateFinding(finding, { user_note: noteValue })}
            type="button"
          >
            <Save size={16} />
            <span>备注</span>
          </button>
        </div>
        <div className="finding-actions__right">
          <SpoilerToggle
            value={selectedSpoiler}
            onChange={(level) =>
              onSetItemSpoilers((current) => ({
                ...current,
                [finding.finding_id]: level,
              }))
            }
          />
          <div className="finding-actions__buttons">
            <button
              className="secondary-command secondary-command--compact"
              onClick={() => onUpdateFinding(finding, { review_status: "confirmed" })}
              type="button"
            >
              <Check size={16} />
              <span>确认</span>
            </button>
            <button
              className="secondary-command secondary-command--compact"
              onClick={() => onUpdateFinding(finding, { review_status: "false_positive" })}
              type="button"
            >
              <X size={16} />
              <span>误报</span>
            </button>
            <button className="secondary-command secondary-command--compact" onClick={() => onOpenContext(finding)} type="button">
              <Eye size={16} />
              <span>上下文</span>
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="scan-config-stack">
      <ReportHistoryPanel
        globalSpoiler={globalSpoiler}
        onDeleteReport={onDeleteReport}
        onExportReport={onExportReport}
        onRefreshReports={onRefreshReports}
        onSetGlobalSpoiler={onSetGlobalSpoiler}
        report={report}
        reports={reports}
        selectedReportId={selectedReportId}
        onSetSelectedReportId={onSetSelectedReportId}
      />

      {report ? (
        <>
          <section className="result-summary-grid">
            <div className="result-panel">
              <strong>发现条目</strong>
              <span>{report.summary.total_findings}</span>
            </div>
            <div className="result-panel">
              <strong>已确认</strong>
              <span>{report.summary.verified_findings}</span>
            </div>
            <div className="result-panel">
              <strong>待复核</strong>
              <span>{report.summary.pending_review}</span>
            </div>
            <div className="result-panel">
              <strong>状态</strong>
              <span>{reportStatusText(report.status, report.compatibility_status)}</span>
            </div>
          </section>

          {reportWarnings.length > 0 ? (
            <section className="report-warning-panel" aria-label="扫描报告警告">
              <ShieldAlert size={18} />
              <div>
                {reportWarnings.map((warning) => (
                  <span key={warning}>{warning}</span>
                ))}
              </div>
            </section>
          ) : null}

          <ResultFilterPanel
            filters={filters}
            onSetFilters={onSetFilters}
            onSetResultView={onSetResultView}
            resultView={resultView}
            ruleOptions={ruleOptions}
          />

          {resultView === "events" ? (
            <EventResults
              expandedEventIds={expandedEventIds}
              filters={filters}
              getFindingSpoiler={getFindingSpoiler}
              onSetExpandedEventIds={onSetExpandedEventIds}
              renderFindingActions={renderFindingActions}
              renderFindingBody={renderFindingBody}
              report={report}
              setEventSpoilerLevel={setEventSpoilerLevel}
              visibleEvents={visibleEvents}
            />
          ) : (
            <FindingTable
              filteredFindings={filteredFindings}
              findingPage={findingPage}
              globalSpoiler={globalSpoiler}
              itemSpoilers={itemSpoilers}
              onSetFindingPage={onSetFindingPage}
              onSetPageSize={onSetPageSize}
              pageSize={pageSize}
              pagedFindings={pagedFindings}
              renderFindingActions={renderFindingActions}
              renderFindingBody={renderFindingBody}
              totalPages={totalPages}
            />
          )}
        </>
      ) : (
        <section className="config-card">
          <span className="empty-state">请选择项目和历史报告。</span>
        </section>
      )}
    </div>
  );
}

function ReportHistoryPanel({
  reports,
  report,
  selectedReportId,
  globalSpoiler,
  onSetSelectedReportId,
  onRefreshReports,
  onExportReport,
  onDeleteReport,
  onSetGlobalSpoiler
}: Pick<
  ResultsTabProps,
  | "reports"
  | "report"
  | "selectedReportId"
  | "globalSpoiler"
  | "onSetSelectedReportId"
  | "onRefreshReports"
  | "onExportReport"
  | "onDeleteReport"
  | "onSetGlobalSpoiler"
>) {
  return (
    <section className="config-card">
      <header className="config-card__header">
        <h3>报告历史</h3>
        <div className="command-row">
          <button className="secondary-command secondary-command--compact" onClick={onRefreshReports} type="button">
            <RefreshCw size={16} />
            <span>刷新</span>
          </button>
          <button className="secondary-command secondary-command--compact" disabled={!report} onClick={() => onExportReport("md")} type="button">
            <FileDown size={16} />
            <span>MD</span>
          </button>
          <button className="secondary-command secondary-command--compact" disabled={!report} onClick={() => onExportReport("json")} type="button">
            <FileDown size={16} />
            <span>JSON</span>
          </button>
          <button className="danger-command" disabled={!report} onClick={() => onDeleteReport()} type="button">
            <Trash2 size={16} />
            <span>删除</span>
          </button>
        </div>
      </header>
      <div className="history-panel">
        <div className="history-list">
          {reports.length === 0 ? (
            <span className="empty-state">暂无报告。先选择扫描标签页启动扫描。</span>
          ) : (
            reports.map((item) => (
              <div
                className={classNames(
                  "history-item",
                  selectedReportId === item.report_id && "history-item--active"
                )}
                key={item.report_id}
              >
                <button
                  className="history-item__restore"
                  onClick={() => onSetSelectedReportId(item.report_id)}
                  type="button"
                >
                  <span className={`status-pill status-pill--${reportStatusClass(item.status, item.compatibility_status)}`}>
                    {reportStatusText(item.status, item.compatibility_status)}
                  </span>
                  <span className="history-item__content">
                    <strong title={item.profile_name}>{item.profile_name}</strong>
                    <small>
                      {item.finding_count} 条 · {formatTime(item.created_at)}
                    </small>
                  </span>
                </button>
                <IconButton
                  label="删除报告"
                  onClick={() => onDeleteReport(item.report_id)}
                >
                  <Trash2 size={16} />
                </IconButton>
              </div>
            ))
          )}
        </div>
      </div>
      <div style={{ marginBottom: 16 }}>
        <span style={{ fontSize: 12, color: "var(--color-muted)", marginRight: 8 }}>全局剧透</span>
        <div className="spoiler-toggle">
          {spoilerOptions.map((opt) => (
            <button
              aria-pressed={globalSpoiler === opt.value ? "true" : undefined}
              key={opt.value}
              onClick={() => onSetGlobalSpoiler(opt.value)}
              type="button"
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <span className="field-hint field-hint--warning">
        AI 扫描结果仅供辅助参考，不能保证覆盖所有雷点或完全避免误判。
      </span>
    </section>
  );
}

function ResultFilterPanel({
  filters,
  resultView,
  ruleOptions,
  onSetFilters,
  onSetResultView
}: Pick<ResultsTabProps, "filters" | "resultView" | "ruleOptions" | "onSetFilters" | "onSetResultView">) {
  return (
    <section className="config-card">
      <header className="config-card__header">
        <h3>筛选</h3>
        <div className="command-row">
          <button
            aria-pressed={resultView === "events"}
            className="secondary-command secondary-command--compact"
            onClick={() => onSetResultView("events")}
            type="button"
          >
            <span>事件视图</span>
          </button>
          <button
            aria-pressed={resultView === "findings"}
            className="secondary-command secondary-command--compact"
            onClick={() => onSetResultView("findings")}
            type="button"
          >
            <span>逐条视图</span>
          </button>
          <button
            className="secondary-command secondary-command--compact"
            onClick={() => onSetFilters(emptyFilters)}
            type="button"
          >
            <X size={16} />
            <span>清空</span>
          </button>
        </div>
      </header>
      <div className="form-grid form-grid--two">
        <SelectField
          label="雷点类型"
          onChange={(event) => onSetFilters((current) => ({ ...current, ruleId: event.target.value }))}
          options={[{ label: "全部", value: "" }, ...ruleOptions]}
          value={filters.ruleId}
        />
        <SelectField
          label="复核状态"
          onChange={(event) =>
            onSetFilters((current) => ({ ...current, reviewStatus: event.target.value }))
          }
          options={reviewOptions}
          value={filters.reviewStatus}
        />
        <NumberInput
          label="最低严重度"
          max={5}
          min={1}
          onChange={(event) =>
            onSetFilters((current) => ({
              ...current,
              minSeverity: Number(event.target.value || "1")
            }))
          }
          value={filters.minSeverity}
        />
        <NumberInput
          label="最低置信度"
          max={1}
          min={0}
          onChange={(event) =>
            onSetFilters((current) => ({
              ...current,
              minConfidence: Number(event.target.value || "0")
            }))
          }
          step={0.05}
          value={filters.minConfidence}
        />
        <TextInput
          label="章节过滤"
          onChange={(event) =>
            onSetFilters((current) => ({ ...current, chapterText: event.target.value }))
          }
          value={filters.chapterText}
        />
        <SelectField
          label="主线"
          onChange={(event) =>
            onSetFilters((current) => ({
              ...current,
              mainPlot: event.target.value as ResultFilters["mainPlot"]
            }))
          }
          options={[
            { label: "全部", value: "all" },
            { label: "主线", value: "main" },
            { label: "非主线", value: "side" }
          ]}
          value={filters.mainPlot}
        />
      </div>
      <ToggleSwitch
        checked={filters.highRiskOnly}
        label="仅显示高置信雷点"
        onChange={(checked) =>
          onSetFilters((current) => ({ ...current, highRiskOnly: checked }))
        }
      />
      <span className="field-hint">严重度 ≥ 4 且置信度 ≥ 0.8</span>
    </section>
  );
}

function EventResults({
  visibleEvents,
  report,
  filters,
  expandedEventIds,
  getFindingSpoiler,
  setEventSpoilerLevel,
  onSetExpandedEventIds,
  renderFindingBody,
  renderFindingActions
}: {
  visibleEvents: ScanEvent[];
  report: ScanReport;
  filters: ResultFilters;
  expandedEventIds: Set<string>;
  getFindingSpoiler: (findingId: string, eventId?: string) => SpoilerLevel;
  setEventSpoilerLevel: (eventId: string, findingIds: string[], level: SpoilerLevel) => void;
  onSetExpandedEventIds: ResultsTabProps["onSetExpandedEventIds"];
  renderFindingBody: (finding: ScanFinding, spoilerLevel: SpoilerLevel) => JSX.Element;
  renderFindingActions: (finding: ScanFinding) => JSX.Element;
}) {
  return (
    <>
      <div className="command-row" style={{ marginBottom: 8 }}>
        <button
          className="secondary-command secondary-command--compact"
          onClick={() => onSetExpandedEventIds(new Set(visibleEvents.map((event) => event.event_id)))}
          type="button"
        >
          <span>全部展开</span>
        </button>
        <button
          className="secondary-command secondary-command--compact"
          onClick={() => onSetExpandedEventIds(new Set())}
          type="button"
        >
          <span>全部收起</span>
        </button>
      </div>
      <section className="event-list">
        {visibleEvents.length === 0 ? (
          <span className="empty-state">暂无符合筛选条件的事件。</span>
        ) : (
          visibleEvents.map((event) => {
            const selectedSpoiler = getFindingSpoiler(event.event_id);
            const related = event.finding_ids
              .map((findingId) =>
                report.findings.find((finding) => finding.finding_id === findingId)
              )
              .filter((finding): finding is ScanFinding => Boolean(finding))
              .filter((finding) => {
                if (filters.reviewStatus && finding.review_status !== filters.reviewStatus) return false;
                return true;
              });
            return (
              <section className="event-card" key={event.event_id}>
                <header className="event-card__header">
                  <div className="event-card__heading">
                    <strong className="event-card__title">{event.rule_name}</strong>
                    <span
                      className="event-card__meta"
                      title={(event.related_chapters.join("、") || event.first_chapter) + ` · 严重度 ${event.max_severity} · 置信度 ${event.max_confidence.toFixed(2)}`}
                    >
                      {event.related_chapters.join("、") || event.first_chapter} · 严重度{" "}
                      {event.max_severity} · 置信度 {event.max_confidence.toFixed(2)}
                    </span>
                  </div>
                  <div className="event-card__actions">
                    <SpoilerToggle
                      value={selectedSpoiler}
                      onChange={(level) =>
                        setEventSpoilerLevel(event.event_id, event.finding_ids, level)
                      }
                    />
                    <button
                      className="secondary-command secondary-command--compact"
                      onClick={() =>
                        onSetExpandedEventIds((prev) => {
                          const next = new Set(prev);
                          if (next.has(event.event_id)) next.delete(event.event_id);
                          else next.add(event.event_id);
                          return next;
                        })
                      }
                      type="button"
                    >
                      <Eye size={16} />
                      <span>{expandedEventIds.has(event.event_id) ? "收起" : "展开"}</span>
                    </button>
                  </div>
                </header>
                <p className="event-summary-text">{event.event_summary[selectedSpoiler]}</p>
                {expandedEventIds.has(event.event_id) ? (
                  <div className="finding-card-list">
                    {related.map((finding) => {
                      const findingSpoiler = getFindingSpoiler(finding.finding_id, event.event_id);
                      return (
                        <section className="finding-card" key={finding.finding_id}>
                          <header className="finding-card__header">
                            <strong>{pathName(finding.chapter_file)} · {finding.paragraph_ids.join(", ")}</strong>
                            {reviewBadge(finding.review_status)}
                          </header>
                          <div className="finding-card__detail">
                            {renderFindingBody(finding, findingSpoiler)}
                          </div>
                          {renderFindingActions(finding)}
                        </section>
                      );
                    })}
                  </div>
                ) : null}
              </section>
            );
          })
        )}
      </section>
    </>
  );
}

function FindingTable({
  filteredFindings,
  pagedFindings,
  itemSpoilers,
  globalSpoiler,
  findingPage,
  pageSize,
  totalPages,
  onSetFindingPage,
  onSetPageSize,
  renderFindingBody,
  renderFindingActions
}: Pick<
  ResultsTabProps,
  | "filteredFindings"
  | "pagedFindings"
  | "itemSpoilers"
  | "globalSpoiler"
  | "findingPage"
  | "pageSize"
  | "totalPages"
  | "onSetFindingPage"
  | "onSetPageSize"
> & {
  renderFindingBody: (finding: ScanFinding, spoilerLevel: SpoilerLevel) => JSX.Element;
  renderFindingActions: (finding: ScanFinding) => JSX.Element;
}) {
  return (
    <section className="table-shell">
      {filteredFindings.length === 0 ? (
        <span className="empty-state">暂无符合筛选条件的条目。</span>
      ) : (
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>规则</th>
                <th>章节</th>
                <th>段落</th>
                <th>风险</th>
                <th>描述</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {pagedFindings.map((finding) => {
                const selectedSpoiler = itemSpoilers[finding.finding_id] ?? globalSpoiler;
                return (
                  <tr key={finding.finding_id}>
                    <td>{finding.rule_name}</td>
                    <td>{pathName(finding.chapter_file)}</td>
                    <td>{finding.paragraph_ids.join(", ")}</td>
                    <td>
                      {finding.severity} / {finding.confidence.toFixed(2)}
                      {finding.is_main_plot ? " / 主线" : ""}
                    </td>
                    <td>
                      {renderFindingBody(finding, selectedSpoiler)}
                    </td>
                    <td>{reviewBadge(finding.review_status)}</td>
                    <td>{renderFindingActions(finding)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, flexWrap: "wrap", gap: 8 }}>
            <div style={{ fontSize: 13, color: "var(--color-muted)" }}>
              共 {filteredFindings.length} 条，每页
              <select
                onChange={(event) => onSetPageSize(Number(event.target.value))}
                style={{ margin: "0 4px", padding: "2px 6px", border: "1px solid var(--color-border)", borderRadius: 4, fontSize: 13 }}
                value={pageSize}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              条
            </div>
            <Pagination
              findingPage={findingPage}
              onSetFindingPage={onSetFindingPage}
              totalPages={totalPages}
            />
          </div>
        </>
      )}
    </section>
  );
}

function Pagination({
  findingPage,
  totalPages,
  onSetFindingPage
}: Pick<ResultsTabProps, "findingPage" | "totalPages" | "onSetFindingPage">) {
  const pages: Array<number | string> = [];
  const range = 2;
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= findingPage - range && i <= findingPage + range)) {
      pages.push(i);
    } else if (pages[pages.length - 1] !== "...") {
      pages.push("...");
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      <button
        className="secondary-command secondary-command--compact"
        disabled={findingPage <= 1}
        onClick={() => onSetFindingPage(1)}
        title="首页"
        type="button"
      >
        «
      </button>
      <button
        className="secondary-command secondary-command--compact"
        disabled={findingPage <= 1}
        onClick={() => onSetFindingPage((page) => page - 1)}
        type="button"
      >
        ‹
      </button>
      {pages.map((page, index) =>
        page === "..." ? (
          <span key={`ellipsis-${index}`} style={{ padding: "0 6px", color: "var(--color-muted)" }}>…</span>
        ) : (
          <button
            className={classNames(
              "secondary-command secondary-command--compact",
              findingPage === page && "primary-command"
            )}
            key={page}
            onClick={() => onSetFindingPage(page as number)}
            style={findingPage === page ? { fontWeight: 700, minWidth: 32 } : { minWidth: 32 }}
            type="button"
          >
            {page}
          </button>
        )
      )}
      <button
        className="secondary-command secondary-command--compact"
        disabled={findingPage >= totalPages}
        onClick={() => onSetFindingPage((page) => page + 1)}
        type="button"
      >
        ›
      </button>
      <button
        className="secondary-command secondary-command--compact"
        disabled={findingPage >= totalPages}
        onClick={() => onSetFindingPage(totalPages)}
        title="末页"
        type="button"
      >
        »
      </button>
    </div>
  );
}

function SpoilerToggle({
  value,
  onChange,
}: {
  value: SpoilerLevel;
  onChange: (level: SpoilerLevel) => void;
}) {
  return (
    <div className="spoiler-toggle">
      {spoilerOptions.map((opt) => (
        <button
          key={opt.value}
          aria-pressed={value === opt.value ? "true" : undefined}
          onClick={() => onChange(opt.value)}
          type="button"
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function reviewBadge(status: string) {
  const cls = `review-badge review-badge--${status}`;
  return <span className={cls}>{reviewStatusText(status)}</span>;
}
