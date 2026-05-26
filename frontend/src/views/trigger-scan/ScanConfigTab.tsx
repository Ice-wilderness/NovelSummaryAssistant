import {
  Play,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  Square,
  X
} from "lucide-react";
import type {
  ApiConfig,
  ProjectRecord,
  ScanFinding,
  TriggerProfile,
  TriggerScanPrecheckResponse,
  TriggerScanReportHistoryItem,
  TaskRecord
} from "../../api/types";
import { apiDisplayName } from "../../api/display";
import { StageProgressBar, type Stage } from "../../components/StageProgressBar";
import {
  NumberInput,
  SelectField,
  ToggleSwitch
} from "../../components/forms/FormControls";
import { formatTime, pathName, statusText, workflowLabel } from "./display";

interface ScanConfigTabProps {
  activeApis: ApiConfig[];
  canPrecheck: boolean;
  canStart: boolean;
  generateSkipAdvice: boolean;
  keepLowConfidence: boolean;
  latestTriggerTask: TaskRecord | null;
  liveFindings: ScanFinding[];
  maxQuoteChars: number;
  minConfidence: number;
  minimumOutputCharacters: number;
  preciseChapterBatchSize: number;
  precheck: TriggerScanPrecheckResponse | null;
  profiles: TriggerProfile[];
  rangeEnd: number | "";
  rangeStart: number;
  reports: TriggerScanReportHistoryItem[];
  resumeReportId: string;
  scanApiIds: string[];
  scanCurrentStage: string;
  scanProjects: ProjectRecord[];
  scanStages: Stage[];
  selectedProfileId: string;
  selectedProjectSlug: string;
  triggerEvents: TaskRecord["events"];
  verificationApiId: string;
  verificationChapterBatchSize: number;
  verificationEnabled: boolean;
  onCancelDecision: () => void;
  onControlTriggerTask: (action: "resume" | "cancel") => void;
  onGenerateSkipAdviceChange: (value: boolean) => void;
  onKeepLowConfidenceChange: (value: boolean) => void;
  onLoadProjects: () => void;
  onMaxQuoteCharsChange: (value: number) => void;
  onMinConfidenceChange: (value: number) => void;
  onMinimumOutputCharactersChange: (value: number) => void;
  onPreciseChapterBatchSizeChange: (value: number) => void;
  onRangeEndChange: (value: number | "") => void;
  onRangeStartChange: (value: number) => void;
  onResumeReportChange: (reportId: string) => void;
  onRunPrecheck: () => void;
  onSaveConfig: () => void;
  onScanApiToggle: (apiId: string, checked: boolean) => void;
  onSelectedProfileChange: (profileId: string) => void;
  onSelectedProjectChange: (projectSlug: string) => void;
  onStartScan: () => void;
  onVerificationApiChange: (apiId: string) => void;
  onVerificationChapterBatchSizeChange: (value: number) => void;
  onVerificationEnabledChange: (value: boolean) => void;
}

export function ScanConfigTab({
  activeApis,
  canPrecheck,
  canStart,
  generateSkipAdvice,
  keepLowConfidence,
  latestTriggerTask,
  liveFindings,
  maxQuoteChars,
  minConfidence,
  minimumOutputCharacters,
  preciseChapterBatchSize,
  precheck,
  profiles,
  rangeEnd,
  rangeStart,
  reports,
  resumeReportId,
  scanApiIds,
  scanCurrentStage,
  scanProjects,
  scanStages,
  selectedProfileId,
  selectedProjectSlug,
  triggerEvents,
  verificationApiId,
  verificationChapterBatchSize,
  verificationEnabled,
  onCancelDecision,
  onControlTriggerTask,
  onGenerateSkipAdviceChange,
  onKeepLowConfidenceChange,
  onLoadProjects,
  onMaxQuoteCharsChange,
  onMinConfidenceChange,
  onMinimumOutputCharactersChange,
  onPreciseChapterBatchSizeChange,
  onRangeEndChange,
  onRangeStartChange,
  onResumeReportChange,
  onRunPrecheck,
  onSaveConfig,
  onScanApiToggle,
  onSelectedProfileChange,
  onSelectedProjectChange,
  onStartScan,
  onVerificationApiChange,
  onVerificationChapterBatchSizeChange,
  onVerificationEnabledChange
}: ScanConfigTabProps) {
  return (
    <div className="scan-config-stack">
      <section className="config-card">
        <header className="config-card__header">
          <h3>项目与档案</h3>
          <div className="command-row">
            <button className="secondary-command secondary-command--compact" onClick={onLoadProjects} type="button">
              <RefreshCw size={16} />
              <span>刷新</span>
            </button>
          </div>
        </header>
        <div className="form-grid form-grid--two">
          <SelectField
            hint="可选择小说总结或章节分割项目。"
            label="扫描项目"
            onChange={(event) => onSelectedProjectChange(event.target.value)}
            options={scanProjects.map((project) => ({
              label: `${project.project_name} · ${workflowLabel(project)}`,
              value: project.project_slug
            }))}
            value={selectedProjectSlug}
          />
          <SelectField
            label="雷点档案"
            onChange={(event) => onSelectedProfileChange(event.target.value)}
            options={profiles.map((profile) => ({ label: profile.name, value: profile.id }))}
            value={selectedProfileId}
          />
        </div>
        <div className="form-grid form-grid--two">
          <SelectField
            hint="选择历史报告以继续扫描未完成章节，或留空开始全新扫描。"
            label="续扫报告"
            onChange={(event) => onResumeReportChange(event.target.value)}
            options={[
              { label: "全新扫描", value: "" },
              ...reports
                .filter((report) => report.status !== "completed")
                .map((report) => ({
                  label: `${formatTime(report.created_at)} · ${report.profile_name} · ${report.finding_count}条 · ${statusText(report.status)}`,
                  value: report.report_id
                }))
            ]}
            value={resumeReportId}
          />
        </div>
      </section>

      <section className="config-card">
        <header className="config-card__header">
          <h3>扫描参数</h3>
          <button
            className="secondary-command secondary-command--compact"
            disabled={!selectedProjectSlug}
            onClick={onSaveConfig}
            type="button"
          >
            <Save size={16} />
            <span>保存配置</span>
          </button>
        </header>
        <div className="form-grid form-grid--two">
          <SelectField
            label="二次验证 API"
            onChange={(event) => onVerificationApiChange(event.target.value)}
            options={activeApis.map((config) => ({
              label: apiDisplayName(config),
              value: config.id
            }))}
            value={verificationApiId}
          />
          <NumberInput
            label="起始章节"
            min={1}
            onChange={(event) => onRangeStartChange(Number(event.target.value || "1"))}
            value={rangeStart}
          />
          <NumberInput
            label="结束章节"
            min={1}
            onChange={(event) => onRangeEndChange(event.target.value ? Number(event.target.value) : "")}
            placeholder="留空为最后一章"
            value={rangeEnd}
          />
          <NumberInput
            label="最低置信度"
            max={1}
            min={0}
            onChange={(event) => onMinConfidenceChange(Number(event.target.value || "0"))}
            step={0.05}
            value={minConfidence}
          />
          <NumberInput
            label="证据引用字数"
            min={1}
            onChange={(event) => onMaxQuoteCharsChange(Number(event.target.value || "80"))}
            value={maxQuoteChars}
          />
          <NumberInput
            label="最少输出字数"
            min={0}
            onChange={(event) => onMinimumOutputCharactersChange(Number(event.target.value || "0"))}
            value={minimumOutputCharacters}
          />
          <NumberInput
            label="精扫每批章节"
            min={1}
            onChange={(event) => onPreciseChapterBatchSizeChange(Number(event.target.value || "5"))}
            value={preciseChapterBatchSize}
          />
          <NumberInput
            label="验证每批章节"
            min={1}
            onChange={(event) => onVerificationChapterBatchSizeChange(Number(event.target.value || "5"))}
            value={verificationChapterBatchSize}
          />
        </div>
        <div className="option-band option-band--split">
          <ToggleSwitch
            checked={keepLowConfidence}
            label="保留低置信度"
            onChange={onKeepLowConfidenceChange}
          />
          <ToggleSwitch
            checked={verificationEnabled}
            label="二次验证"
            onChange={onVerificationEnabledChange}
          />
          <ToggleSwitch
            checked={generateSkipAdvice}
            label="生成跳读建议"
            onChange={onGenerateSkipAdviceChange}
          />
        </div>
      </section>

      <section className="config-card">
        <header className="config-card__header">
          <h3>扫描 API</h3>
          <span className="field-hint">{scanApiIds.length} 个已选</span>
        </header>
        {activeApis.length === 0 ? (
          <span className="empty-state">暂无启用 API，请先在「API 配置」页启用。</span>
        ) : (
          <div className="checkbox-list">
            {activeApis.map((config) => (
              <label className="check-row" key={config.id}>
                <input
                  checked={scanApiIds.includes(config.id)}
                  onChange={(event) => onScanApiToggle(config.id, event.target.checked)}
                  type="checkbox"
                />
                <span>{apiDisplayName(config)}</span>
              </label>
            ))}
          </div>
        )}
      </section>

      <section className="config-card">
        <header className="config-card__header">
          <h3>启动检查</h3>
          <div className="command-row">
            <button
              className="secondary-command"
              disabled={!canPrecheck}
              onClick={onRunPrecheck}
              type="button"
            >
              <Search size={17} />
              <span>预检</span>
            </button>
            <button
              className="secondary-command"
              disabled={latestTriggerTask?.status !== "paused"}
              onClick={() => onControlTriggerTask("resume")}
              type="button"
            >
              <Play size={17} />
              <span>恢复</span>
            </button>
            <button
              className="secondary-command"
              disabled={!latestTriggerTask || !["pending", "running", "paused"].includes(latestTriggerTask.status)}
              onClick={() => onControlTriggerTask("cancel")}
              type="button"
            >
              <Square size={16} />
              <span>取消</span>
            </button>
            <button
              className="primary-command"
              disabled={!canStart}
              onClick={onStartScan}
              type="button"
            >
              <ShieldAlert size={17} />
              <span>开始扫描</span>
            </button>
          </div>
        </header>
        {precheck ? (
          <div className="precheck-panel">
            <div className="result-panel result-panel--compact">
              <strong>{precheck.ready ? "预检通过" : "需要处理"}</strong>
              <span>
                {precheck.pending_chapter_count > 0 && precheck.pending_chapter_count < precheck.selected_chapter_count
                  ? `${precheck.pending_chapter_count} 章待扫描（已完成 ${precheck.completed_chapter_count} 章）`
                  : `${precheck.selected_chapter_count}/${precheck.chapter_count} 章将被扫描`}
              </span>
            </div>
            {precheck.errors.length > 0 ? (
              <div className="precheck-list precheck-list--error">
                {precheck.errors.map((error) => (
                  <span key={error}>{error}</span>
                ))}
              </div>
            ) : null}
            {precheck.warnings.length > 0 ? (
              <div className="precheck-list">
                {precheck.warnings.map((warning) => (
                  <span key={warning}>{warning}</span>
                ))}
              </div>
            ) : null}
            {precheck.decisions.length > 0 ? (
              <div className="command-row">
                <button className="secondary-command secondary-command--compact" onClick={onCancelDecision} type="button">
                  <X size={16} />
                  <span>取消决策</span>
                </button>
              </div>
            ) : null}
          </div>
        ) : (
          <span className="empty-state">点击预检后会显示扫描前置检查结果。</span>
        )}
      </section>

      <section className="config-card">
        <header className="config-card__header">
          <h3>实时进度</h3>
          <span className={`status-pill status-pill--${latestTriggerTask?.status ?? "idle"}`}>
            {statusText(latestTriggerTask?.status ?? "")}
          </span>
        </header>
        {latestTriggerTask ? (
          <>
            {scanStages.length > 0 && (
              <StageProgressBar stages={scanStages} currentStage={scanCurrentStage} />
            )}
            <div className="project-progress-panel">
              <header>
                <strong>{latestTriggerTask.progress_text || latestTriggerTask.task_id}</strong>
                <span>{latestTriggerTask.result_summary || latestTriggerTask.error || "等待事件"}</span>
              </header>
              <div className="progress-event-list">
                {triggerEvents.slice(-8).map((event) => (
                  <div className="progress-event-row" key={`${event.task_id}-${event.timestamp}-${event.message}`}>
                    <span>{event.progress_text || event.event_type}</span>
                    <strong>{event.message}</strong>
                  </div>
                ))}
              </div>
            </div>
            {liveFindings.length > 0 ? (
              <div className="live-finding-list">
                {liveFindings.map((finding) => (
                  <div className="result-panel result-panel--compact" key={finding.finding_id}>
                    <strong>{finding.rule_name}</strong>
                    <span>
                      {pathName(finding.chapter_file)} · 严重度 {finding.severity} · 置信度{" "}
                      {finding.confidence.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </>
        ) : (
          <span className="empty-state">暂无雷点扫描任务。</span>
        )}
      </section>
    </div>
  );
}
