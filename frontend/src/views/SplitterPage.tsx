import { Play } from "lucide-react";
import { useState } from "react";
import { apiClient } from "../api/client";
import {
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
import { GuidancePanel } from "../components/common/Guidance";
import { useManagedProject } from "../hooks/useManagedProject";
import { usePathPicker } from "../hooks/usePathPicker";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useTaskActions } from "../hooks/useTaskActions";

type SplitterMode = "default" | "regex" | "title_list";

export function SplitterPage() {
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory } = usePathPicker();
  const project = useManagedProject("chapter_split");
  const { startTask } = useTaskActions();
  const [mode, setMode] = useState<SplitterMode>("default");
  const [customPattern, setCustomPattern] = useState("");
  const [titleListText, setTitleListText] = useState("");
  const [handleVolumes, setHandleVolumes] = useState(true);
  const titleList = titleListText
    .split(/\r?\n/)
    .map((title) => title.trim())
    .filter(Boolean);
  const canStart =
    project.uploadedFileIds.length === 1 &&
    (mode !== "regex" || customPattern.trim().length > 0) &&
    (mode !== "title_list" || titleList.length > 0) &&
    !isTaskBusy;

  const startSplitter = () => {
    void (async () => {
      const savedProject = await project.saveProject();
      if (!savedProject) {
        return;
      }
      await startTask(() =>
        apiClient.startSplitter({
          source_txt_file_path: "",
          output_directory_path: "",
          mode,
          custom_pattern: customPattern,
          title_list: titleList,
          handle_volumes: handleVolumes,
          project_name: savedProject.project_name,
          project_slug: savedProject.project_slug,
          uploaded_file_ids: savedProject.uploads.filter((file) => !file.missing).map((file) => file.id),
          custom_output_directory_path: savedProject.custom_output_directory
        })
      );
    })();
  };

  return (
    <section className="workflow-view">
      <div className="view-header">
        <div>
          <h2>章节分割</h2>
          <span>{mode === "default" ? "默认模式" : mode === "regex" ? "正则模式" : "标题列表"}</span>
        </div>
        <button
          className="primary-command"
          disabled={!canStart}
          onClick={startSplitter}
          title="启动章节分割任务"
          type="button"
        >
          <Play size={18} />
          <span>开始</span>
        </button>
      </div>

      <GuidancePanel
        title="章节分割流程"
        items={[
          "上传待切分的整本小说 TXT 文件后，切分结果默认保存到项目导出目录。",
          "默认模式按内置章节识别规则处理；正则模式使用你提供的表达式；标题列表模式按给定标题切分。",
          "系统会固定输出一章一个 TXT 文件，分卷处理会尽量保留卷级顺序。"
        ]}
      />

      <section className="config-card">
        <header className="config-card__header">
          <h3>项目与文件</h3>
          <ProjectActionRow
            canSave={project.isProjectDirty}
            onImport={() => void pickDirectory("导入章节分割项目目录", project.importProjectFromDirectory)}
            onSave={() => void project.saveProject()}
          />
        </header>
        <span className="field-hint">章节分割每次只需要上传一个源 TXT 文件；导入项目后会统计已生成的 TXT 文件。</span>
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
          hint="选择一个 .txt 文件作为拆章源文件。"
          isUploading={project.isUploading}
          label="源 TXT"
          multiple={false}
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
          hint="决定章节边界的识别方式。"
          label="模式"
          onChange={(event) => setMode(event.target.value as SplitterMode)}
          options={[
            { label: "默认", value: "default" },
            { label: "正则", value: "regex" },
            { label: "标题列表", value: "title_list" }
          ]}
          value={mode}
        />
      </div>

      <section className="option-band option-band--split">
        <ToggleSwitch checked={handleVolumes} label="分卷处理" onChange={setHandleVolumes} />
      </section>

      {mode === "regex" ? (
        <TextAreaField
          hint="填写能匹配章节标题的正则表达式。"
          label="正则表达式"
          onChange={(event) => setCustomPattern(event.target.value)}
          value={customPattern}
        />
      ) : null}

      {mode === "title_list" ? (
        <TextAreaField
          hint="每行一个章节标题，按列表顺序进行匹配。"
          label="标题列表"
          onChange={(event) => setTitleListText(event.target.value)}
          value={titleListText}
        />
      ) : null}
    </section>
  );
}
