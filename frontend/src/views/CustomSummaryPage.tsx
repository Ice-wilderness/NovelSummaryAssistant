import { Play } from "lucide-react";
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
import { useManagedProject } from "../hooks/useManagedProject";
import { usePathPicker } from "../hooks/usePathPicker";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useTaskActions } from "../hooks/useTaskActions";
import { useAppState } from "../state/AppState";

export function CustomSummaryPage() {
  const { state } = useAppState();
  const { startTask } = useTaskActions();
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory } = usePathPicker();
  const project = useManagedProject("custom_summary");
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

  const startCustomSummary = () => {
    void startTask(() =>
      apiClient.startCustomSummary({
        selected_file_paths: [],
        user_prompt: userPrompt,
        api_id: selectedApiId,
        project_name: project.projectName,
        project_slug: project.projectSlug,
        uploaded_file_ids: project.uploadedFileIds,
        custom_output_directory_path: project.customOutputDirectory
      })
    );
  };

  return (
    <section className="workflow-view">
      <div className="view-header">
        <div>
          <h2>自定义总结</h2>
          <span>{project.uploadedFileIds.length} 个文件</span>
        </div>
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

      <GuidancePanel
        title="自定义总结流程"
        items={[
          "上传参考材料 .txt 文件后，任务会读取这些文件并按你填写的自定义指令生成结果。",
          "API 决定本次任务使用哪个模型配置；未手动选择时默认使用第一个启用 API。",
          "自定义指令是本工作流的核心提示词，不会覆盖提示词页面中的持久化节点。"
        ]}
      />

      <section className="config-card">
        <header className="config-card__header">
          <h3>项目与文件</h3>
          <ProjectActionRow
            canSave={Boolean(project.projectSlug)}
            onImport={() => void pickDirectory("导入自定义总结项目目录", project.importProjectFromDirectory)}
            onSave={() => void project.saveProjectName()}
          />
        </header>
        <span className="field-hint">历史项目会恢复上传文件、输出目录和最近任务状态。</span>
        <div className="form-grid form-grid--two">
          <ProjectHistoryField
            onRestore={project.restoreProject}
            projects={project.projects}
            value={project.projectSlug}
          />
          <TextInput
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
          outputDirectory={project.outputDirectory}
          onBrowseOutputDirectory={() =>
            void pickDirectory("选择输出目录", project.setOutputDirectory)
          }
          onOpenOutputDirectory={project.openOutputDirectory}
          onOutputDirectoryChange={project.setOutputDirectory}
          onUseDefaultDirectory={project.useDefaultOutputDirectory}
          onValidateOutputDirectory={() => void project.validateOutputDirectory()}
        />
        <ProjectProgressPanel progress={project.progress} />
        {project.message ? <span className="field-hint">{project.message}</span> : null}
        {[...project.warnings, project.error].filter(Boolean).map((warning) => (
          <span className="field-hint field-hint--warning" key={warning}>
            {warning}
          </span>
        ))}
      </section>

      <div className="form-grid form-grid--two">
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
        <div className="result-panel result-panel--compact">
          <strong>结果</strong>
          <span>{latestCustomTask?.result_summary || latestCustomTask?.progress_text || "暂无结果"}</span>
        </div>
      </div>
      <TextAreaField
        hint="描述你希望模型如何阅读、提取和输出这些文件内容。"
        label="自定义指令"
        onChange={(event) => setUserPrompt(event.target.value)}
        value={userPrompt}
      />
    </section>
  );
}
