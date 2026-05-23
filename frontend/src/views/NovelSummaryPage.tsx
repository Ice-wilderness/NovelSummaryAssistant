import { ListChecks, Play } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "../api/client";
import { defaultNovelWordCounts } from "../api/defaults";
import { apiDisplayName } from "../api/display";
import type { NovelWordCounts, ProjectRecord, SummaryOutputFormat } from "../api/types";
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

export function NovelSummaryPage() {
  const { state } = useAppState();
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory } = usePathPicker();
  const project = useManagedProject("novel_summary");
  const { startTask } = useTaskActions();
  const activeApis = useMemo(
    () => state.apiConfigs.filter((config) => config.is_active),
    [state.apiConfigs]
  );
  const [activeApiIds, setActiveApiIds] = useState<string[]>([]);
  const [summaryBatchSize, setSummaryBatchSize] = useState(10);
  const [summaryOutputFormat, setSummaryOutputFormat] = useState<SummaryOutputFormat>("md");
  const [bigSummaryBatchSize, setBigSummaryBatchSize] = useState(5);
  const [superSummaryThreshold, setSuperSummaryThreshold] = useState(5);
  const [ultimateApiId, setUltimateApiId] = useState("");
  const [useFineGrainedFlow, setUseFineGrainedFlow] = useState(false);
  const [wordCounts, setWordCounts] = useState<NovelWordCounts>(defaultNovelWordCounts);
  const [liveStages, setLiveStages] = useState<Stage[]>([]);
  const [liveCurrentStage, setLiveCurrentStage] = useState("");
  const eventsRef = useRef(state.events);
  eventsRef.current = state.events;

  // 监听 SSE 进度事件，提取 stages 数据供 StageProgressBar 实时更新
  useEffect(() => {
    const latest = state.events;
    if (latest.length === 0) return;
    // 从后往前找最近的 progress 事件
    for (let i = latest.length - 1; i >= 0; i--) {
      const ev = latest[i];
      if (ev.event_type === "progress" && ev.data?.stages) {
        const stages = ev.data.stages as Stage[];
        const currentStage = (ev.data.current_stage as string) || "";
        setLiveStages(stages);
        setLiveCurrentStage(currentStage);
        return;
      }
    }
  }, [state.events]);

  // 项目切换时清除实时进度
  useEffect(() => {
    setLiveStages([]);
    setLiveCurrentStage("");
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

  const updateWordCount = (key: keyof NovelWordCounts, value: string) => {
    setWordCounts((current) => ({ ...current, [key]: value }));
  };

  const toggleApi = (apiId: string, checked: boolean) => {
    setActiveApiIds((current) =>
      checked ? [...new Set([...current, apiId])] : current.filter((id) => id !== apiId)
    );
  };

  const ensureGranularityReady = async (savedProject: ProjectRecord) => {
    if (!savedProject.requires_granularity_migration) {
      return savedProject;
    }

    const shouldMigrate = window.confirm(
      `检测到 ${savedProject.legacy_grouped_file_count} 个旧版多章合并文件。继续总结前需要迁移为单章文件，迁移后小总结合并章节数将使用 ${savedProject.summary_batch_size}。\n\n是否现在迁移？`
    );
    if (!shouldMigrate) {
      return null;
    }

    try {
      const result = await apiClient.migrateChapterGranularity(savedProject.project_slug);
      setSummaryBatchSize(result.project.summary_batch_size);
      await project.refreshProjectState();
      return result.project;
    } catch (directError) {
      const directMessage = directError instanceof Error ? directError.message : String(directError);
      const useOriginalTxt = window.confirm(
        `直接解析合并文件失败：${directMessage}\n\n是否选择原始整本 TXT 重新拆分？`
      );
      if (!useOriginalTxt) {
        return null;
      }
      const sourceTxtPath = await apiClient.pickFile("选择原始整本 TXT");
      if (!sourceTxtPath) {
        return null;
      }
      const result = await apiClient.migrateChapterGranularity(
        savedProject.project_slug,
        sourceTxtPath
      );
      setSummaryBatchSize(result.project.summary_batch_size);
      await project.refreshProjectState();
      return result.project;
    }
  };

  const startNovelTask = (stopAfterSmallSummary: boolean) => {
    void (async () => {
      const savedProject = await project.saveProject({
        summary_output_format: summaryOutputFormat
      });
      if (!savedProject) {
        return;
      }
      const runnableProject = await ensureGranularityReady(savedProject);
      if (!runnableProject) {
        return;
      }
      await startTask(() =>
        (stopAfterSmallSummary
          ? apiClient.startSmallSummaryPreparation
          : apiClient.startNovelSummary)({
          source_folder_path: "",
          active_api_ids: activeApiIds,
          summary_batch_size: runnableProject.summary_batch_size || summaryBatchSize,
          summary_output_format: summaryOutputFormat,
          big_summary_batch_size: bigSummaryBatchSize,
          super_summary_threshold: superSummaryThreshold,
          ultimate_api_id: ultimateApiId,
          use_fine_grained_flow: useFineGrainedFlow,
          stop_after_small_summary: stopAfterSmallSummary,
          word_counts: wordCounts,
          project_name: runnableProject.project_name,
          project_slug: runnableProject.project_slug,
          uploaded_file_ids: runnableProject.uploads.filter((file) => !file.missing).map((file) => file.id),
          custom_output_directory_path: runnableProject.custom_output_directory
        })
      );
    })();
  };
  const startNovelSummary = () => startNovelTask(false);
  const startSmallSummaryOnly = () => startNovelTask(true);
  const isOutputFormatDirty =
    Boolean(project.savedProject) &&
    summaryOutputFormat !== project.savedProject?.summary_output_format;
  const canStart =
    project.uploadedFileIds.length > 0 &&
    activeApiIds.length > 0 &&
    summaryBatchSize > 0 &&
    bigSummaryBatchSize > 0 &&
    superSummaryThreshold > 0 &&
    !isTaskBusy;

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
            canSave={project.isProjectDirty || isOutputFormatDirty}
            onImport={() => void pickDirectory("导入旧小说项目目录", project.importProjectFromDirectory)}
            onSave={() =>
              void project.saveProject({
                summary_output_format: summaryOutputFormat
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
        <UploadFileField
          files={project.uploadedFiles}
          hint="可选择多个章节 .txt 文件，上传顺序会保留。"
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
        {project.message ? <span className="field-hint">{project.message}</span> : null}
        {[...project.warnings, project.error].filter(Boolean).map((warning) => (
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
