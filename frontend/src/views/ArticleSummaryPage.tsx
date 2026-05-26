import { Play } from "lucide-react";
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

  return (
    <section className="workflow-view">
      <div className="view-header">
        <div>
          <h2>文章总结</h2>
          <span>{project.uploadedFileIds.length} 个文件</span>
        </div>
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

      <GuidancePanel
        title="文章总结流程"
        items={[
          "上传一个或多个 .txt 文章文件后，系统会按上传顺序建立项目输入并生成段落总结。",
          "段落总结会先处理每个选中文件，最终总结会整合所有段落摘要。",
          "输出目录会默认填入项目导出目录；需要改到别处时，直接修改或选择新的输出目录。"
        ]}
      />

      <section className="config-card">
        <header className="config-card__header">
          <h3>项目与文件</h3>
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
        <SummaryPartialNotice task={latestArticleTask} kind="article" />
      </section>

      <div className="form-grid form-grid--two">
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
    </section>
  );
}
