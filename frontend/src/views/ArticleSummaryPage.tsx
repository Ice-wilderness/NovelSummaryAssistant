import { FileText, FolderClock, Play, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { apiClient } from "../api/client";
import { defaultArticleWordCounts } from "../api/defaults";
import type { ArticleWordCounts } from "../api/types";
import { GuidancePanel } from "../components/common/Guidance";
import {
  OutputDirectoryField,
  ProjectActionRow,
  ProjectHistoryField,
  ProjectProgressPanel,
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

export function ArticleSummaryPage() {
  const { state } = useAppState();
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory } = usePathPicker();
  const project = useManagedProject("article_summary");
  const { startTask } = useTaskActions();
  const [wordCounts, setWordCounts] = useState<ArticleWordCounts>(defaultArticleWordCounts);
  const latestArticleTask = state.taskOrder
    .map((taskId) => state.tasks[taskId])
    .find((task) => task.task_type === "article_summary");

  const updateWordCount = (key: keyof ArticleWordCounts, value: string) => {
    setWordCounts((current) => ({ ...current, [key]: value }));
  };

  const startArticleSummary = () => {
    void (async () => {
      const savedProject = await project.saveProject();
      if (!savedProject) {
        return;
      }
      await startTask(() =>
        apiClient.startArticleSummary({
        source_folder_path: "",
        selected_files: [],
        output_subfolder: "",
        word_counts: wordCounts,
        project_name: savedProject.project_name,
        project_slug: savedProject.project_slug,
        uploaded_file_ids: savedProject.uploads.filter((file) => !file.missing).map((file) => file.id),
        custom_output_directory_path: savedProject.custom_output_directory
        })
      );
    })();
  };
  const canStart = project.uploadedFileIds.length > 0 && !isTaskBusy;
  const taskSummary = latestArticleTask ? taskHeadline(latestArticleTask) : "上传文章后建立总结任务";
  const terminalMessage = taskTerminalMessage(latestArticleTask ?? null);

  return (
    <section className="workflow-view support-studio summary-studio">
      <StudioMotionSurface className="support-hero support-hero--article">
        <div className="support-hero__copy">
          <span>Article Summary Studio</span>
          <h2>文章总结</h2>
          <p>{taskSummary}</p>
        </div>
        <div className="support-hero__stats">
          <StudioStatusBadge tone={canStart ? "success" : project.uploadedFileIds.length ? "warning" : "muted"}>
            {canStart ? "可以开始" : project.uploadedFileIds.length ? "等待任务空闲" : "等待上传"}
          </StudioStatusBadge>
          <StudioStatusBadge tone={taskStatusTone(latestArticleTask?.status)}>
            {taskStatusLabel(latestArticleTask?.status)}
          </StudioStatusBadge>
          <span>{project.uploadedFileIds.length} 个文件</span>
          <span>{project.projects.length} 个历史项目</span>
        </div>
        <div className="command-row support-hero__actions">
        <button
          className="primary-command"
          disabled={!canStart}
          onClick={startArticleSummary}
          title="启动文章总结任务"
          type="button"
        >
          <Play size={18} />
          <span>开始</span>
        </button>
        </div>
      </StudioMotionSurface>

      <div className="support-flow-guide">
        <GuidancePanel
          title="文章总结流程"
          items={[
            "上传一个或多个 .txt 文章文件后，系统会按上传顺序建立项目输入并生成段落总结。",
            "段落总结会先处理每个选中文件，最终总结会整合所有段落摘要。",
            "输出目录会默认填入项目导出目录；需要改到别处时，直接修改或选择新的输出目录。"
          ]}
        />
      </div>

      <div className="support-work-grid support-work-grid--summary">
        <div className="support-main-stack">
          <StudioMotionSurface className="support-panel support-project-panel">
            <header className="support-panel__header">
              <div>
                <span><FolderClock size={15} /> 项目指挥区</span>
                <h3>项目与文件</h3>
              </div>
              <ProjectActionRow
                canSave={project.canSaveProject}
                isSaving={project.isSaving}
                lastSavedAt={project.lastSavedAt}
                onImport={() => void pickDirectory("导入旧文章项目目录", project.importProjectFromDirectory)}
                onSave={() => void project.saveProject()}
              />
            </header>
            <span className="field-hint">可从历史项目恢复未完成的文章总结；导入旧项目会读取已有段落/最终总结进度。</span>
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
              hint="支持多选 .txt 文件，列表顺序就是提交给任务的顺序。"
              isUploading={project.isUploading}
              label="文章文件"
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
                <span><SlidersHorizontal size={15} /> 输出配方</span>
                <h3>字数设置</h3>
              </div>
            </header>
            <div className="form-grid">
              <TextInput
                label="段落总结字数"
                onChange={(event) => updateWordCount("section", event.target.value)}
                value={wordCounts.section}
              />
              <TextInput
                label="最终总结字数"
                onChange={(event) => updateWordCount("final", event.target.value)}
                value={wordCounts.final}
              />
            </div>
          </StudioMotionSurface>

          <StudioMotionSurface className="support-panel support-result-panel">
            <header className="support-panel__header">
              <div>
                <span><FileText size={15} /> 任务反馈</span>
                <h3>结果与异常</h3>
              </div>
            </header>
            <div className="support-terminal-card">
              <strong>{taskStatusLabel(latestArticleTask?.status)}</strong>
              <span>{terminalMessage || latestArticleTask?.result_summary || latestArticleTask?.progress_text || "暂无结果"}</span>
            </div>
            <SummaryPartialNotice task={latestArticleTask} kind="article" />
          </StudioMotionSurface>
        </aside>
      </div>
    </section>
  );
}
