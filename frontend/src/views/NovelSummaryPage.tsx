import { AlertTriangle, Eye, ListChecks, Play, Wrench } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "../api/client";
import { defaultNovelWordCounts } from "../api/defaults";
import { apiDisplayName } from "../api/display";
import type {
  ChapterPreviewItem,
  OutputCheck,
  ProjectRecord,
  ProjectRepairRequest,
  RepairAction,
  SummaryOutputFormat,
  NovelWordCounts
} from "../api/types";
import { assertFilesWithinUploadLimit } from "../api/uploadLimits";
import { PatternSelector } from "../components/patterns/PatternSelector";
import { SplitPreviewPanel } from "../components/splitting/SplitPreviewPanel";
import { StageProgressBar, type Stage } from "../components/StageProgressBar";
import { GuidancePanel } from "../components/common/Guidance";
import {
  NumberInput,
  OutputDirectoryField,
  ProjectActionRow,
  ProjectHistoryField,
  ProjectProgressPanel,
  SelectField,
  TextInput,
  TextAreaField,
  ToggleSwitch,
  UploadFileField
} from "../components/forms/FormControls";
import { useManagedProject } from "../hooks/useManagedProject";
import { usePathPicker } from "../hooks/usePathPicker";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useTaskActions } from "../hooks/useTaskActions";
import { useAppState } from "../state/AppState";

const novelWordCountFields: Array<{ key: keyof NovelWordCounts; label: string }> = [
  { key: "small_summary_word_count", label: "小结总结" },
  { key: "small_plot_word_count", label: "小结剧情" },
  { key: "small_char_word_count", label: "小结角色" },
  { key: "big_plot_word_count", label: "大结剧情" },
  { key: "big_char_word_count", label: "大结角色" },
  { key: "super_plot_p1_word_count", label: "超级剧情 P1" },
  { key: "super_plot_p2_word_count", label: "超级剧情 P2" },
  { key: "super_char_p1_word_count", label: "超级角色 P1" },
  { key: "super_char_p2_word_count", label: "超级角色 P2" },
  { key: "ultimate_plot_p1_word_count", label: "终极剧情 P1" },
  { key: "ultimate_plot_p2_word_count", label: "终极剧情 P2" },
  { key: "ultimate_char_p1_word_count", label: "终极角色 P1" },
  { key: "ultimate_char_p2_word_count", label: "终极角色 P2" }
];

const MAX_VISIBLE_REPAIR_ITEMS = 3;

function uniqueItems(items: string[]) {
  return items.filter((item, index) => item && items.indexOf(item) === index);
}

function reconciliationStatusText(status: string) {
  switch (status) {
    case "ok":
      return "产物正常";
    case "incomplete":
      return "未完成";
    case "abnormal_completed":
      return "异常完成";
    case "state_incomplete":
      return "状态待校正";
    case "unsupported":
      return "暂不支持";
    default:
      return status || "待检查";
  }
}

function outputCheckStatusText(status: string) {
  switch (status) {
    case "present":
      return "存在";
    case "missing":
      return "缺失";
    case "format_mismatch":
      return "格式不一致";
    default:
      return status || "待检查";
  }
}

function repairActionStatusText(status: string) {
  return status === "blocked" ? "不可执行" : "可执行";
}

function repairRisks(action: RepairAction) {
  return [
    action.requires_llm ? "可能调用 LLM" : "",
    action.may_change_content ? "内容可能变化" : "",
    action.may_overwrite ? "可能覆盖文件" : ""
  ].filter(Boolean);
}

function compactList(items: string[], emptyText = "无") {
  const unique = uniqueItems(items);
  if (unique.length === 0) {
    return emptyText;
  }
  const visible = unique.slice(0, MAX_VISIBLE_REPAIR_ITEMS);
  const suffix = unique.length > visible.length ? ` 等 ${unique.length} 项` : "";
  return `${visible.join("、")}${suffix}`;
}

function filteredProjectWarnings(project: ProjectRecord | null, warnings: string[], error: string) {
  const reconciliationMessages = new Set(
    (project?.reconciliation_warnings || []).map((warning) => warning.message)
  );
  return uniqueItems([...warnings, error].filter(Boolean)).filter(
    (warning) => !reconciliationMessages.has(warning)
  );
}

interface ProjectRepairPanelProps {
  project: ProjectRecord | null;
  isBusy: boolean;
  repairError: string;
  onStartRepair: (action: RepairAction) => void;
}

function ProjectRepairPanel({
  project,
  isBusy,
  repairError,
  onStartRepair
}: ProjectRepairPanelProps) {
  const status = String(project?.reconciliation_status || "");
  const warnings = project?.reconciliation_warnings || [];
  const checks = project?.output_checks || [];
  const actions = project?.repair_plan?.actions || [];
  const warningMessages = uniqueItems(warnings.map((warning) => warning.message));
  const visibleWarningMessages = warningMessages.slice(0, MAX_VISIBLE_REPAIR_ITEMS);
  const failedChecks = checks.filter((check) => check.status !== "present");
  const visibleFailedChecks = failedChecks.slice(0, MAX_VISIBLE_REPAIR_ITEMS);
  const shouldShow =
    Boolean(repairError) ||
    Boolean(status && status !== "ok" && status !== "incomplete") ||
    warnings.length > 0 ||
    failedChecks.length > 0 ||
    actions.length > 0;

  if (!shouldShow) {
    return null;
  }

  return (
    <section className="repair-panel" aria-label="项目修复建议">
      <header className="repair-panel__header">
        <span className={`status-pill status-pill--${status || "idle"}`}>
          <AlertTriangle size={13} />
          <span>{reconciliationStatusText(status)}</span>
        </span>
        <strong>项目产物检查</strong>
      </header>
      {status === "abnormal_completed" ? (
        <span className="field-hint field-hint--warning">
          最近任务状态仍按历史记录保留；当前问题是已完成记录对应的输出产物缺失或不一致。
        </span>
      ) : null}
      {status === "state_incomplete" ? (
        <span className="field-hint field-hint--warning">
          检测到已有输出产物，但缺少可靠的完成状态记录。
        </span>
      ) : null}
      {warningMessages.length > 0 ? (
        <div className="repair-summary-row">
          <strong>{warningMessages.length} 条产物警告</strong>
          <span>{visibleWarningMessages.join("；")}</span>
          {warningMessages.length > visibleWarningMessages.length ? (
            <details className="repair-details">
              <summary>查看全部警告</summary>
              <ul>
                {warningMessages.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : null}
      {failedChecks.length > 0 ? (
        <div className="repair-check-list">
          <span className="field-hint">
            {failedChecks.length} 项输出检查未通过，下面显示优先处理项。
          </span>
          {visibleFailedChecks.map((check: OutputCheck) => (
            <div className="repair-check-row" key={check.id || check.label}>
              <span>{check.label}</span>
              <strong>{outputCheckStatusText(check.status)}</strong>
              <small>{check.message || check.expected || check.actual}</small>
            </div>
          ))}
          {failedChecks.length > visibleFailedChecks.length ? (
            <details className="repair-details">
              <summary>查看全部 {failedChecks.length} 项输出检查</summary>
              <ul>
                {failedChecks.map((check) => (
                  <li key={`${check.id}-${check.expected}`}>
                    {check.label}：{outputCheckStatusText(check.status)}；{check.message || check.expected || check.actual}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : null}
      {actions.length > 0 ? (
        <div className="repair-action-list">
          {actions.map((action) => {
            const risks = repairRisks(action);
            const blocked = action.status === "blocked";
            return (
              <article
                className={`repair-action ${blocked ? "repair-action--blocked" : ""}`}
                key={action.action_id}
              >
                <header>
                  <strong>{action.label}</strong>
                  <span className={`status-pill status-pill--${blocked ? "idle" : "success"}`}>
                    {repairActionStatusText(action.status)}
                  </span>
                </header>
                <span>{action.description}</span>
                {action.required_inputs.length > 0 ? (
                  <small>需要：{compactList(action.required_inputs)}</small>
                ) : null}
                {action.affected_outputs.length > 0 ? (
                  <>
                    <small>影响：{compactList(action.affected_outputs)}</small>
                    {action.affected_outputs.length > MAX_VISIBLE_REPAIR_ITEMS ? (
                      <details className="repair-details repair-details--compact">
                        <summary>查看全部影响输出</summary>
                        <ul>
                          {action.affected_outputs.map((output) => (
                            <li key={output}>{output}</li>
                          ))}
                        </ul>
                      </details>
                    ) : null}
                  </>
                ) : null}
                {risks.length > 0 ? <small>确认：{risks.join("、")}</small> : null}
                {blocked ? (
                  <span className="field-hint field-hint--warning">
                    {action.blocked_reason || "该修复动作当前不可执行。"}
                  </span>
                ) : (
                  <button
                    className="secondary-command secondary-command--compact"
                    disabled={isBusy}
                    onClick={() => onStartRepair(action)}
                    type="button"
                  >
                    <Wrench size={16} />
                    <span>{isBusy ? "处理中..." : "执行修复"}</span>
                  </button>
                )}
              </article>
            );
          })}
        </div>
      ) : null}
      {repairError ? (
        <span className="field-hint field-hint--warning">{repairError}</span>
      ) : null}
    </section>
  );
}

export function NovelSummaryPage() {
  const { state } = useAppState();
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory } = usePathPicker();
  const project = useManagedProject("novel_summary");
  const handleTaskTerminal = useCallback(() => {
    void project.refreshProjectState();
  }, [project.refreshProjectState]);
  const { startTask, watchTask } = useTaskActions({ onTaskTerminal: handleTaskTerminal });
  const activeApis = useMemo(
    () => state.apiConfigs.filter((config) => config.is_active),
    [state.apiConfigs]
  );
  const [activeApiIds, setActiveApiIds] = useState<string[]>([]);
  const [summaryBatchSize, setSummaryBatchSize] = useState(10);
  const [summaryOutputFormat, setSummaryOutputFormat] = useState<SummaryOutputFormat>("md");
  const [bigSummaryBatchSize, setBigSummaryBatchSize] = useState(5);
  const [superSummaryThreshold, setSuperSummaryThreshold] = useState(10);
  const [ultimateApiId, setUltimateApiId] = useState("");
  const [useFineGrainedFlow, setUseFineGrainedFlow] = useState(false);
  const [wordCounts, setWordCounts] = useState<NovelWordCounts>(defaultNovelWordCounts);
  const [liveStages, setLiveStages] = useState<Stage[]>([]);
  const [liveCurrentStage, setLiveCurrentStage] = useState("");
  const [repairError, setRepairError] = useState("");
  const [isRepairing, setIsRepairing] = useState(false);
  const eventsRef = useRef(state.events);
  eventsRef.current = state.events;

  // 源文件分割状态
  type SplitMode = "default" | "regex" | "title_list";
  const [splitMode, setSplitMode] = useState<SplitMode>("default");
  const [selectedPatternId, setSelectedPatternId] = useState("");
  const [handleVolumes, setHandleVolumes] = useState(true);
  const [titleListText, setTitleListText] = useState("");
  const [previewChapters, setPreviewChapters] = useState<ChapterPreviewItem[] | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [splitIngesting, setSplitIngesting] = useState(false);
  const [sourceUploading, setSourceUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const titleList = titleListText
    .split(/\r?\n/)
    .map((t) => t.trim())
    .filter(Boolean);

  // 源文件（本地状态，不上传到项目）
  const [sourceFile, setSourceFileState] = useState<File | null>(null);
  const [sourceContent, setSourceContent] = useState("");

  // 已分割章节：直接来自 project uploads（源文件不经过此处）
  const chapterFiles = project.uploadedFiles;
  const chapterFileIds = project.uploadedFileIds;
  const activeNovelTaskIds = useMemo(() => {
    if (!project.projectSlug) {
      return new Set<string>();
    }
    return new Set(
      state.taskOrder
        .map((taskId) => state.tasks[taskId])
        .filter((task) => {
          if (!task) {
            return false;
          }
          if (!["novel_summary", "small_summary_preparation", "project_repair"].includes(String(task.task_type))) {
            return false;
          }
          if (["cancelled", "partial_failed", "success", "failed", "interrupted"].includes(task.status)) {
            return false;
          }
          const params = task.params_summary as Record<string, unknown>;
          return String(params.project_slug || "") === project.projectSlug;
        })
        .map((task) => task.task_id)
    );
  }, [project.projectSlug, state.taskOrder, state.tasks]);

  // 上传源文件（本地读取，不进项目）
  const handleSourceUpload = async (fileList: FileList | File[]) => {
    const files = Array.from(fileList);
    if (files.length === 0) return;
    setSourceUploading(true);
    setPreviewChapters(null);
    setPreviewError("");
    try {
      const file = files[0];
      assertFilesWithinUploadLimit([file]);
      const buf = await file.arrayBuffer();
      let content: string;
      const utf8 = new TextDecoder("utf-8", { fatal: false }).decode(buf);
      if (!utf8.includes("�") && !utf8.includes("\0")) {
        content = utf8;
      } else {
        try {
          content = new TextDecoder("gbk", { fatal: true }).decode(buf);
        } catch {
          content = utf8;
        }
      }
      setSourceFileState(file);
      setSourceContent(content);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "读取文件失败");
    } finally {
      setSourceUploading(false);
    }
  };

  // 清除源文件
  const clearSourceFile = () => {
    setSourceFileState(null);
    setSourceContent("");
    setPreviewChapters(null);
    setPreviewError("");
  };

  // 切换分割模式或参数时清除旧的预览结果
  const clearPreview = () => {
    setPreviewChapters(null);
    setPreviewError("");
  };
  useEffect(clearPreview, [splitMode, selectedPatternId, handleVolumes, titleListText]);
  useEffect(clearPreview, [project.uploadedFileIds]);

  // 监听 SSE 进度事件，提取 stages 数据供 StageProgressBar 实时更新
  useEffect(() => {
    const latest = state.events;
    if (latest.length === 0 || activeNovelTaskIds.size === 0) {
      setLiveStages([]);
      setLiveCurrentStage("");
      return;
    }
    // 从后往前找最近的 progress 事件
    for (let i = latest.length - 1; i >= 0; i--) {
      const ev = latest[i];
      if (
        activeNovelTaskIds.has(ev.task_id) &&
        ev.event_type === "progress" &&
        ev.data?.stages
      ) {
        const stages = ev.data.stages as Stage[];
        const currentStage = (ev.data.current_stage as string) || "";
        setLiveStages(stages);
        setLiveCurrentStage(currentStage);
        return;
      }
    }
    setLiveStages([]);
    setLiveCurrentStage("");
  }, [activeNovelTaskIds, state.events]);

  // 项目切换时清除实时进度
  useEffect(() => {
    setLiveStages([]);
    setLiveCurrentStage("");
    setRepairError("");
  }, [project.projectSlug]);

  useEffect(() => {
    if (activeApiIds.length === 0 && activeApis.length > 0) {
      setActiveApiIds(activeApis.map((config) => config.id));
      setUltimateApiId(activeApis[0].id);
    }
  }, [activeApiIds.length, activeApis]);

  useEffect(() => {
    if (ultimateApiId && !activeApiIds.includes(ultimateApiId) && activeApiIds.length > 0) {
      setUltimateApiId(activeApiIds[0]);
    }
  }, [activeApiIds, ultimateApiId]);

  useEffect(() => {
    const savedBatchSize = project.savedProject?.summary_batch_size;
    if (savedBatchSize && savedBatchSize > 0) {
      setSummaryBatchSize(savedBatchSize);
    }
  }, [project.savedProject?.summary_batch_size]);

  useEffect(() => {
    const savedFormat = project.savedProject?.summary_output_format;
    if (savedFormat === "md" || savedFormat === "txt") {
      setSummaryOutputFormat(savedFormat);
      return;
    }
    if (!project.projectSlug) {
      setSummaryOutputFormat("md");
    }
  }, [project.projectSlug, project.savedProject?.summary_output_format]);

  useEffect(() => {
    setUseFineGrainedFlow(Boolean(project.savedProject?.use_fine_grained_flow));
  }, [project.projectSlug, project.savedProject?.use_fine_grained_flow]);

  const updateWordCount = (key: keyof NovelWordCounts, value: string) => {
    setWordCounts((current) => ({ ...current, [key]: value }));
  };

  const toggleApi = (apiId: string, checked: boolean) => {
    setActiveApiIds((current) =>
      checked ? [...new Set([...current, apiId])] : current.filter((id) => id !== apiId)
    );
  };

  const startNovelTask = (stopAfterSmallSummary: boolean) => {
    void (async () => {
      const savedProject = await project.saveProject({
        summary_output_format: summaryOutputFormat,
        summary_batch_size: summaryBatchSize,
        use_fine_grained_flow: useFineGrainedFlow
      });
      if (!savedProject) {
        return;
      }
      await startTask(() =>
        (stopAfterSmallSummary
          ? apiClient.startSmallSummaryPreparation
          : apiClient.startNovelSummary)({
          source_folder_path: "",
          active_api_ids: activeApiIds,
          summary_batch_size: summaryBatchSize,
          summary_output_format: summaryOutputFormat,
          big_summary_batch_size: bigSummaryBatchSize,
          super_summary_threshold: superSummaryThreshold,
          ultimate_api_id: ultimateApiId,
          use_fine_grained_flow: useFineGrainedFlow,
          stop_after_small_summary: stopAfterSmallSummary,
          word_counts: wordCounts,
          project_name: savedProject.project_name,
          project_slug: savedProject.project_slug,
          uploaded_file_ids: savedProject.uploads.filter((file) => !file.missing).map((file) => file.id),
          custom_output_directory_path: savedProject.custom_output_directory
        })
      );
    })();
  };
  const startNovelSummary = () => startNovelTask(false);
  const startSmallSummaryOnly = () => startNovelTask(true);

  const startProjectRepair = async (action: RepairAction) => {
    if (!project.projectSlug || action.status === "blocked") {
      return;
    }
    const risks = repairRisks(action);
    if (risks.length > 0) {
      const confirmed = window.confirm(
        `执行「${action.label}」？\n\n${risks.join("、")}。修复会作为新的项目任务记录。`
      );
      if (!confirmed) {
        return;
      }
    }
    const request: ProjectRepairRequest = {
      action_id: action.action_id,
      confirm_llm: action.requires_llm || undefined,
      confirm_content_change: action.may_change_content || undefined,
      confirm_overwrite: action.may_overwrite || undefined,
      big_summary_batch_size: bigSummaryBatchSize,
      super_summary_threshold: superSummaryThreshold,
      ultimate_api_id: ultimateApiId,
      word_counts: wordCounts
    };
    setIsRepairing(true);
    setRepairError("");
    try {
      const task = await apiClient.startProjectRepair(project.projectSlug, request);
      watchTask(task);
    } catch (error) {
      setRepairError(error instanceof Error ? error.message : "启动修复失败");
      await project.refreshProjectState();
    } finally {
      setIsRepairing(false);
    }
  };
  // 预览分割
  const previewSplit = async () => {
    if (!sourceContent) return;
    setPreviewChapters(null);
    setPreviewError("");
    setPreviewLoading(true);
    try {
      const result = await apiClient.previewSplit({
        file_content: sourceContent,
        mode: splitMode,
        pattern_config_id: splitMode === "regex" ? selectedPatternId : undefined,
        title_list: splitMode === "title_list" ? titleList : undefined,
        handle_volumes: handleVolumes,
      });
      setPreviewChapters(result.chapters);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "预览失败");
    } finally {
      setPreviewLoading(false);
    }
  };

  // 确认分割并导入到项目章节
  const confirmSplitAndIngest = async () => {
    if (!sourceContent) return;
    const savedProject = await project.saveProject({
      summary_output_format: summaryOutputFormat,
      summary_batch_size: summaryBatchSize,
      use_fine_grained_flow: useFineGrainedFlow,
    });
    if (!savedProject) return;
    setSplitIngesting(true);
    try {
      // 直接传 file_content，后端写临时文件后分割
      await apiClient.startSplitter({
        source_txt_file_path: "",
        output_directory_path: "",
        file_content: sourceContent,
        mode: splitMode,
        custom_pattern: "",
        title_list: splitMode === "title_list" ? titleList : [],
        handle_volumes: handleVolumes,
        context: "novel_summary",
        pattern_config_id: splitMode === "regex" ? selectedPatternId : undefined,
        project_name: savedProject.project_name,
        project_slug: savedProject.project_slug,
        uploaded_file_ids: [],
      });
      setSourceFileState(null);
      setSourceContent("");
      await project.refreshProjectState();
      setPreviewChapters(null);
    } catch (err) {
      setPreviewError(err instanceof Error ? `分割失败：${err.message}` : "分割失败");
    } finally {
      setSplitIngesting(false);
    }
  };

  const canPreviewSplit =
    sourceContent.length > 0 &&
    (splitMode !== "regex" || selectedPatternId.length > 0) &&
    (splitMode !== "title_list" || titleList.length > 0) &&
    !isTaskBusy && !splitIngesting;

  const canStart =
    chapterFileIds.length > 0 &&
    activeApiIds.length > 0 &&
    summaryBatchSize > 0 &&
    bigSummaryBatchSize > 0 &&
    superSummaryThreshold > 0 &&
    !isTaskBusy;
  const pageWarnings = filteredProjectWarnings(
    project.savedProject,
    project.warnings,
    project.error
  );

  return (
    <section className="workflow-view">
      <div className="view-header">
        <div>
          <h2>小说总结</h2>
          <span>{activeApis.length} 个可用 API</span>
        </div>
        <div className="command-row">
          <button
            className="secondary-command"
            disabled={!canStart}
            onClick={startSmallSummaryOnly}
            title="只生成小总结"
            type="button"
          >
            <ListChecks size={18} />
            <span>仅小总结</span>
          </button>
          <button
            className="primary-command"
            disabled={!canStart}
            onClick={startNovelSummary}
            title="启动小说总结任务"
            type="button"
          >
            <Play size={18} />
            <span>开始</span>
          </button>
        </div>
      </div>

      <GuidancePanel
        title="小说总结流程"
        items={[
          "上传章节 .txt 文件后，系统会保存到项目工作区，并把生成结果写入项目默认导出目录。",
          "API 选择分为三层：第1层在「API 配置」页全局启用；第2层在此勾选参与并行处理的 API；第3层从已勾选的 API 中选一个执行最终终极总结。",
          "「精细流程」开关决定超级总结阶段的协作方式（开启后所有 API 先一起完成小总结和大总结，再统一进入超级总结；关闭时各 API 独立跑完全流程）。"
        ]}
      />

      <section className="config-card">
        <header className="config-card__header">
          <h3>项目与文件</h3>
          <ProjectActionRow
            canSave={project.canSaveProject}
            isSaving={project.isSaving}
            lastSavedAt={project.lastSavedAt}
            onImport={() => void pickDirectory("导入旧小说项目目录", project.importProjectFromDirectory)}
            onSave={() =>
              void project.saveProject({
                summary_output_format: summaryOutputFormat,
                summary_batch_size: summaryBatchSize,
                use_fine_grained_flow: useFineGrainedFlow
              })
            }
          />
        </header>
        <span className="field-hint">项目名用于组织上传文件、断点缓存和导出目录；导入旧项目会读取已有总结进度。</span>
        <div className="form-grid form-grid--two">
          <ProjectHistoryField
            onDelete={project.deleteProject}
            onNewProject={project.startNewProject}
            onRestore={project.restoreProject}
            projects={project.projects}
            value={project.projectSlug}
          />
          <TextInput
            className="project-name-control"
            hint="未填写时会根据上传文件名自动生成。"
            label="项目名称"
            onChange={(event) => project.setProjectName(event.target.value)}
            value={project.projectName}
          />
        </div>
        {/* ── 源文件分割区域 ── */}
        <div className="split-source-section">
          <h4 className="section-divider">源文件（待分割）</h4>
          <span className="field-hint">上传整本小说 TXT 源文件，选择分割模式，预览确认后直接导入为项目章节。</span>
          <section
            className={`upload-field file-list-field ${isDragging ? "upload-field--dragging" : ""}`}
            onDragLeave={() => setIsDragging(false)}
            onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; setIsDragging(true); }}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleSourceUpload(e.dataTransfer.files); }}
          >
            <header className="file-list-header">
              <span className="file-list-title">
                <span className="field-label">源 TXT 文件</span>
                {sourceFile ? <span className="field-hint">{sourceFile.name}</span> : <span className="field-hint">0 个文件</span>}
              </span>
              {sourceFile ? (
                <button className="secondary-command secondary-command--compact" onClick={clearSourceFile} type="button">
                  清除
                </button>
              ) : null}
            </header>
            {!sourceFile ? (
              <label className="upload-command">
                <span>{sourceUploading ? "读取中..." : "拖拽 .txt 文件到此处或点击选择"}</span>
                <input
                  accept=".txt,text/plain"
                  className="upload-input"
                  disabled={sourceUploading}
                  onChange={(e) => { if (e.target.files) { void handleSourceUpload(e.target.files); e.target.value = ""; } }}
                  type="file"
                />
              </label>
            ) : null}
          </section>
          <div className="form-grid form-grid--two">
            <SelectField
              hint="决定章节边界的识别方式。"
              label="分割模式"
              onChange={(event) => setSplitMode(event.target.value as SplitMode)}
              options={[
                { label: "默认", value: "default" },
                { label: "正则", value: "regex" },
                { label: "标题列表", value: "title_list" }
              ]}
              value={splitMode}
            />
          </div>
          <section className="option-band option-band--split">
            {splitMode !== "title_list" ? (
              <ToggleSwitch checked={handleVolumes} label="分卷处理" onChange={setHandleVolumes} />
            ) : null}
          </section>
          {splitMode === "regex" ? (
            <PatternSelector configId={selectedPatternId} onChange={setSelectedPatternId} />
          ) : null}
          {splitMode === "title_list" ? (
            <TextAreaField
              hint="每行一个章节标题，按列表顺序进行匹配。"
              label="标题列表"
              onChange={(event) => setTitleListText(event.target.value)}
              value={titleListText}
            />
          ) : null}
          <div className="split-source-actions">
            <button
              className="secondary-command"
              disabled={!canPreviewSplit}
              onClick={() => { void previewSplit(); }}
              type="button"
            >
              <Eye size={16} />
              <span>预览分割</span>
            </button>
          </div>
          <SplitPreviewPanel
            chapters={previewChapters}
            loading={previewLoading}
            error={previewError}
            onConfirm={() => { void confirmSplitAndIngest(); }}
            onCancel={() => setPreviewChapters(null)}
          />
        </div>

        <h4 className="section-divider">已分割章节</h4>
        <UploadFileField
          files={chapterFiles}
          hint="手动上传已分割的章节文件；确认分割后章节会自动出现在此处。"
          isUploading={project.isUploading}
          label="章节文件"
          multiple
          onClear={() => void project.clearUploadedFiles()}
          onRemove={project.removeUploadedFile}
          onUpload={project.uploadFiles}
        />
        <OutputDirectoryField
          defaultDirectory={project.defaultOutputDirectory}
          outputDirectory={project.outputDirectory}
          onBrowseOutputDirectory={() =>
            void pickDirectory("选择输出目录", project.setOutputDirectory)
          }
          onOpenOutputDirectory={project.openOutputDirectory}
          onOutputDirectoryChange={project.setOutputDirectory}
          onUseDefaultDirectory={project.useDefaultOutputDirectory}
          onValidateOutputDirectory={() => void project.validateOutputDirectory()}
        />
        {liveStages.length > 0 ? (
          <StageProgressBar stages={liveStages} currentStage={liveCurrentStage} />
        ) : project.progress?.stages ? (
          <StageProgressBar
            stages={project.progress.stages.map((s) => ({
              id: s.label,
              label: s.label,
              completed: s.completed,
              total: s.total,
              status: s.completed > 0 && s.completed >= (s.total || s.completed) ? "completed" as const
                : s.completed > 0 ? "running" as const
                : "pending" as const,
            }))}
            currentStage=""
          />
        ) : null}
        <ProjectProgressPanel progress={project.progress} />
        <ProjectRepairPanel
          isBusy={isTaskBusy || isRepairing}
          onStartRepair={(action) => { void startProjectRepair(action); }}
          project={project.savedProject}
          repairError={repairError}
        />
        {project.message ? <span className="field-hint">{project.message}</span> : null}
        {pageWarnings.map((warning) => (
          <span className="field-hint field-hint--warning" key={warning}>
            {warning}
          </span>
        ))}
      </section>

      <section className="config-card">
        <header className="config-card__header">
          <h3>API 选择</h3>
          <span className="field-hint">勾选并行 API → 选择最终总结 API（按层级：勾选后才能在下方下拉中选择）</span>
        </header>
        <div className="form-grid form-grid--two">
          <div className="field-shell">
            <span className="field-label">并行处理 API</span>
            <span className="field-hint">勾选的 API 会并行执行小总结、大总结和超级总结阶段</span>
            {activeApis.length === 0 ? (
              <span className="empty-state">暂无启用 API，请先在「API 配置」页全局启用</span>
            ) : (
              <div className="checkbox-list">
                {activeApis.map((config) => (
                  <label className="check-row" key={config.id}>
                    <input
                      checked={activeApiIds.includes(config.id)}
                      onChange={(event) => toggleApi(config.id, event.target.checked)}
                      type="checkbox"
                    />
                    <span>{apiDisplayName(config)}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
          <SelectField
            hint="从上方已勾选的 API 中选择一个，用于最后的终极剧情和角色总结"
            label="最终总结 API"
            onChange={(event) => setUltimateApiId(event.target.value)}
            options={activeApis
              .filter((config) => activeApiIds.includes(config.id))
              .map((config) => ({
                label: apiDisplayName(config),
                value: config.id
              }))}
            value={ultimateApiId}
          />
        </div>
      </section>

      <section className="config-card">
        <header className="config-card__header">
          <h3>任务参数</h3>
        </header>
        <div className="form-grid form-grid--two">
          <NumberInput
            hint="每次小总结读取的连续章节数。"
            label="小总结合并章节数"
            min={1}
            onChange={(event) => setSummaryBatchSize(Number(event.target.value))}
            value={summaryBatchSize}
          />
          <SelectField
            hint="总结工作流产物的文件扩展名。"
            label="总结输出格式"
            onChange={(event) => setSummaryOutputFormat(event.target.value as SummaryOutputFormat)}
            options={[
              { label: "Markdown (.md)", value: "md" },
              { label: "TXT (.txt)", value: "txt" }
            ]}
            value={summaryOutputFormat}
          />
          <NumberInput
            hint="每多少个小总结合并成一组大总结。"
            label="大总结批量"
            min={1}
            onChange={(event) => setBigSummaryBatchSize(Number(event.target.value))}
            value={bigSummaryBatchSize}
          />
          <NumberInput
            hint="达到多少个大总结后触发超级总结阶段。"
            label="超级总结阈值"
            min={1}
            onChange={(event) => setSuperSummaryThreshold(Number(event.target.value))}
            value={superSummaryThreshold}
          />
        </div>
        <div className="flow-mode-section">
          <ToggleSwitch
            checked={useFineGrainedFlow}
            label="精细流程"
            onChange={setUseFineGrainedFlow}
          />
          <div className="flow-mode-description">
            {useFineGrainedFlow ? (
              <div className="guidance-panel">
                <p>
                  <strong>精细模式（阶段集中处理）：</strong>
                  所有 API 先并行完成各自的小总结和大总结阶段。全部完成后，系统自动将大总结结果按「超级总结阈值」分批，轮流分配给各 API 执行超级总结。最后再由「最终总结 API」执行终极总结。适合需要检查中间结果、或希望各阶段整齐收束后再进入下一阶段的场景。
                </p>
              </div>
            ) : (
              <div className="guidance-panel">
                <p>
                  <strong>流水线模式（并行独立处理）：</strong>
                  各 API 独立跑完 小总结 → 大总结 → 超级总结 的完整流程，互不等待。所有 API 完成后，由「最终总结 API」执行终极总结。处理速度更快，适合完全自动化、无需人工检查各阶段中间结果的场景。
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="word-count-section">
        <h3>字数设置</h3>
        <div className="word-count-grid">
          {novelWordCountFields.map((field) => (
            <TextInput
              key={field.key}
              label={field.label}
              onChange={(event) => updateWordCount(field.key, event.target.value)}
              value={wordCounts[field.key]}
            />
          ))}
        </div>
      </section>
    </section>
  );
}
