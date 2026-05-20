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

export function ArticleSummaryPage() {
  const { startTask } = useTaskActions();
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory } = usePathPicker();
  const project = useManagedProject("article_summary");
  const [wordCounts, setWordCounts] = useState<ArticleWordCounts>(defaultArticleWordCounts);

  const updateWordCount = (key: keyof ArticleWordCounts, value: string) => {
    setWordCounts((current) => ({ ...current, [key]: value }));
  };

  const startArticleSummary = () => {
    void startTask(() =>
      apiClient.startArticleSummary({
        source_folder_path: "",
        selected_files: [],
        output_subfolder: "",
        word_counts: wordCounts,
        project_name: project.projectName,
        project_slug: project.projectSlug,
        uploaded_file_ids: project.uploadedFileIds,
        custom_output_directory_path: project.customOutputDirectory
      })
    );
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
          "未选择自定义输出目录时，结果写入项目默认导出目录。"
        ]}
      />

      <section className="config-card">
        <header className="config-card__header">
          <h3>项目与文件</h3>
          <ProjectActionRow
            canSave={Boolean(project.projectSlug)}
            onImport={() => void pickDirectory("导入旧文章项目目录", project.importProjectFromDirectory)}
            onSave={() => void project.saveProjectName()}
          />
        </header>
        <span className="field-hint">可从历史项目恢复未完成的文章总结；导入旧项目会读取已有段落/最终总结进度。</span>
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
          hint="支持多选 .txt 文件，列表顺序就是提交给任务的顺序。"
          isUploading={project.isUploading}
          label="文章文件"
          multiple
          onRemove={project.removeUploadedFile}
          onUpload={project.uploadFiles}
        />
        <OutputDirectoryField
          customDirectory={project.customOutputDirectory}
          defaultDirectory={project.defaultOutputDirectory}
          onBrowseCustomDirectory={() =>
            void pickDirectory("选择自定义输出目录", project.setCustomOutputDirectory)
          }
          onCustomDirectoryChange={project.setCustomOutputDirectory}
          onOpenCustomDirectory={project.openCustomDirectory}
          onOpenDefaultDirectory={project.openDefaultDirectory}
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
