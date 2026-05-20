import { Play } from "lucide-react";
import { useState } from "react";
import { apiClient } from "../api/client";
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
import { GuidancePanel } from "../components/common/Guidance";
import { useManagedProject } from "../hooks/useManagedProject";
import { usePathPicker } from "../hooks/usePathPicker";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useTaskActions } from "../hooks/useTaskActions";

type SplitterMode = "default" | "regex" | "title_list";

export function SplitterPage() {
  const { startTask } = useTaskActions();
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory } = usePathPicker();
  const project = useManagedProject("chapter_split");
  const [mode, setMode] = useState<SplitterMode>("default");
  const [chaptersPerFile, setChaptersPerFile] = useState(1);
  const [customPattern, setCustomPattern] = useState("");
  const [titleListText, setTitleListText] = useState("");
  const [handleVolumes, setHandleVolumes] = useState(true);
  const titleList = titleListText
    .split(/\r?\n/)
    .map((title) => title.trim())
    .filter(Boolean);
  const canStart =
    project.uploadedFileIds.length === 1 &&
    chaptersPerFile > 0 &&
    (mode !== "regex" || customPattern.trim().length > 0) &&
    (mode !== "title_list" || titleList.length > 0) &&
    !isTaskBusy;

  const startSplitter = () => {
    void startTask(() =>
      apiClient.startSplitter({
        source_txt_file_path: "",
        output_directory_path: "",
        mode,
        chapters_per_file: chaptersPerFile,
        custom_pattern: customPattern,
        title_list: titleList,
        handle_volumes: handleVolumes,
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
          "每文件章节数控制合并粒度，分卷处理会尽量保留卷级结构。"
        ]}
      />

      <section className="config-card">
        <header className="config-card__header">
          <h3>项目与文件</h3>
          <ProjectActionRow
            canSave={Boolean(project.projectSlug)}
            onImport={() => void pickDirectory("导入章节分割项目目录", project.importProjectFromDirectory)}
            onSave={() => void project.saveProjectName()}
          />
        </header>
        <span className="field-hint">章节分割每次只需要上传一个源 TXT 文件；导入项目后会统计已生成的 TXT 文件。</span>
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
          hint="选择一个 .txt 文件作为拆章源文件。"
          isUploading={project.isUploading}
          label="源 TXT"
          multiple={false}
          onClear={() => void project.clearUploadedFiles()}
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
        <NumberInput
          hint="大于 1 时会把多个连续章节合并到一个输出文件。"
          label="每文件章节数"
          min={1}
          onChange={(event) => setChaptersPerFile(Number(event.target.value))}
          value={chaptersPerFile}
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
