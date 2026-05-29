import { FileText, MessageSquareText, Play, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import { apiClient } from "../api/client";
import { apiDisplayName } from "../api/display";
import { GuidancePanel } from "../components/common/Guidance";
import {
  OutputDirectoryField,
  ProjectActionRow,
  ProjectHistoryField,
  ProjectProgressPanel,
  SelectField,
  TextAreaField,
  TextInput,
  UploadFileField
} from "../components/forms/FormControls";
import { StudioMotionSurface, StudioStatusBadge } from "../components/studio/StudioPrimitives";
import {
  taskHeadline,
  taskStatusLabel,
  taskStatusTone,
  taskTerminalMessage
} from "../components/studio/taskPresentation";
import { useManagedProject } from "../hooks/useManagedProject";
import { usePathPicker } from "../hooks/usePathPicker";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useTaskActions } from "../hooks/useTaskActions";
import { useAppState } from "../state/AppState";
import { SummaryPartialNotice } from "./SummaryPartialNotice";

export function CustomSummaryPage() {
  const { state } = useAppState();
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory } = usePathPicker();
  const project = useManagedProject("custom_summary");
  const { startTask } = useTaskActions();
  const activeApis = useMemo(
    () => state.apiConfigs.filter((config) => config.is_active),
    [state.apiConfigs]
  );
  const latestCustomTask = state.taskOrder
    .map((taskId) => state.tasks[taskId])
    .find((task) => task.task_type === "custom_summary");
  const [userPrompt, setUserPrompt] = useState("");
  const [apiId, setApiId] = useState("");
  const selectedApiId = apiId || activeApis[0]?.id || "";
  const canStart =
    project.uploadedFileIds.length > 0 &&
    userPrompt.trim().length > 0 &&
    selectedApiId.length > 0 &&
    !isTaskBusy;
  const taskSummary = latestCustomTask ? taskHeadline(latestCustomTask) : "上传材料并写入本次专属指令";
  const terminalMessage = taskTerminalMessage(latestCustomTask ?? null);

  const startCustomSummary = () => {
    void (async () => {
      const savedProject = await project.saveProject();
      if (!savedProject) {
        return;
      }
      await startTask(() =>
        apiClient.startCustomSummary({
        selected_file_paths: [],
        user_prompt: userPrompt,
        api_id: selectedApiId,
        project_name: savedProject.project_name,
        project_slug: savedProject.project_slug,
        uploaded_file_ids: savedProject.uploads.filter((file) => !file.missing).map((file) => file.id),
        custom_output_directory_path: savedProject.custom_output_directory
        })
      );
    })();
  };

  return (
    <section className="workflow-view support-studio summary-studio">
      <StudioMotionSurface className="support-hero support-hero--custom">
        <div className="support-hero__copy">
          <span>Custom Summary Studio</span>
          <h2>自定义总结</h2>
          <p>{taskSummary}</p>
        </div>
        <div className="support-hero__stats">
          <StudioStatusBadge tone={canStart ? "success" : project.uploadedFileIds.length ? "warning" : "muted"}>
            {canStart ? "可以开始" : project.uploadedFileIds.length ? "补全指令或 API" : "等待上传"}
          </StudioStatusBadge>
          <StudioStatusBadge tone={taskStatusTone(latestCustomTask?.status)}>
            {taskStatusLabel(latestCustomTask?.status)}
          </StudioStatusBadge>
          <span>{project.uploadedFileIds.length} 个文件</span>
          <span>{activeApis.length} 个启用 API</span>
        </div>
        <div className="command-row support-hero__actions">
        <button
          className="primary-command"
          disabled={!canStart}
          onClick={startCustomSummary}
          title="启动自定义总结任务"
          type="button"
        >
          <Play size={18} />
          <span>开始</span>
        </button>
        </div>
      </StudioMotionSurface>

      <div className="support-flow-guide">
        <GuidancePanel
          title="自定义总结流程"
          items={[
            "上传参考材料 .txt 文件后，任务会读取这些文件并按你填写的自定义指令生成结果。",
            "API 决定本次任务使用哪个模型配置；未手动选择时默认使用第一个启用 API。",
            "自定义指令是本工作流的核心提示词，不会覆盖提示词页面中的持久化节点。"
          ]}
        />
      </div>

      <div className="support-work-grid support-work-grid--summary">
        <div className="support-main-stack">
          <StudioMotionSurface className="support-panel support-project-panel">
            <header className="support-panel__header">
              <div>
                <span><FileText size={15} /> 材料工作区</span>
                <h3>项目与文件</h3>
              </div>
              <ProjectActionRow
                canSave={project.canSaveProject}
                isSaving={project.isSaving}
                lastSavedAt={project.lastSavedAt}
                onImport={() => void pickDirectory("导入自定义总结项目目录", project.importProjectFromDirectory)}
                onSave={() => void project.saveProject()}
              />
            </header>
            <span className="field-hint">历史项目会恢复上传文件、输出目录和最近任务状态。</span>
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
              hint="支持多选 .txt 文件，系统会在后端工作区读取这些文件。"
              isUploading={project.isUploading}
              label="参考材料"
              multiple
              onClear={() => void project.clearUploadedFiles()}
              onRemove={project.removeUploadedFile}
              onUpload={project.uploadFiles}
            />
            <OutputDirectoryField
              defaultDirectory={project.defaultOutputDirectory}
              error={project.outputDirectoryError}
              outputDirectory={project.outputDirectory}
              onBrowseOutputDirectory={() =>
                void pickDirectory("选择输出目录", project.setOutputDirectory, project.setOutputDirectoryError)
              }
              onOpenOutputDirectory={project.openOutputDirectory}
              onOutputDirectoryChange={project.setOutputDirectory}
              onUseDefaultDirectory={project.useDefaultOutputDirectory}
              onValidateOutputDirectory={() => void project.validateOutputDirectory()}
            />
            <ProjectProgressPanel progress={project.progress} />
            {project.message ? <span className="field-hint">{project.message}</span> : null}
            {[...project.warnings, project.error].filter(Boolean).map((warning) => (
              <span className="field-hint field-hint--warning support-warning-pop" key={warning}>
                {warning}
              </span>
            ))}
          </StudioMotionSurface>
        </div>

        <aside className="support-side-stack">
          <StudioMotionSurface className="support-panel support-recipe-panel">
            <header className="support-panel__header">
              <div>
                <span><SlidersHorizontal size={15} /> 运行配方</span>
                <h3>API 与结果</h3>
              </div>
            </header>
            <SelectField
              hint="用于执行本次自定义总结的 API 配置。"
              label="API"
              onChange={(event) => setApiId(event.target.value)}
              options={activeApis.map((config) => ({
                label: apiDisplayName(config),
                value: config.id
              }))}
              value={selectedApiId}
            />
            <div className="support-terminal-card">
              <strong>{taskStatusLabel(latestCustomTask?.status)}</strong>
              <span>{terminalMessage || latestCustomTask?.result_summary || latestCustomTask?.progress_text || "暂无结果"}</span>
            </div>
            <SummaryPartialNotice task={latestCustomTask} kind="custom" />
          </StudioMotionSurface>
        </aside>
      </div>

      <StudioMotionSurface className="support-panel custom-prompt-panel">
        <header className="support-panel__header">
          <div>
            <span><MessageSquareText size={15} /> Prompt Draft</span>
            <h3>自定义指令</h3>
          </div>
        </header>
        <TextAreaField
          hint="描述你希望模型如何阅读、提取和输出这些文件内容。"
          label="自定义指令"
          onChange={(event) => setUserPrompt(event.target.value)}
          value={userPrompt}
        />
      </StudioMotionSurface>
    </section>
  );
}
