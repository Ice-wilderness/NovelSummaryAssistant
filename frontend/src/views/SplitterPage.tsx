import { Play } from "lucide-react";
import { useState } from "react";
import { apiClient } from "../api/client";
import {
  NumberInput,
  PathInput,
  SelectField,
  TextAreaField,
  ToggleSwitch
} from "../components/forms/FormControls";
import { GuidancePanel } from "../components/common/Guidance";
import { usePathPicker } from "../hooks/usePathPicker";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useTaskActions } from "../hooks/useTaskActions";

type SplitterMode = "default" | "regex" | "title_list";

export function SplitterPage() {
  const { startTask } = useTaskActions();
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory, pickFile } = usePathPicker();
  const [sourceTxtFilePath, setSourceTxtFilePath] = useState("");
  const [outputDirectoryPath, setOutputDirectoryPath] = useState("");
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
    sourceTxtFilePath.trim().length > 0 &&
    outputDirectoryPath.trim().length > 0 &&
    chaptersPerFile > 0 &&
    (mode !== "regex" || customPattern.trim().length > 0) &&
    (mode !== "title_list" || titleList.length > 0) &&
    !isTaskBusy;

  const startSplitter = () => {
    void startTask(() =>
      apiClient.startSplitter({
        source_txt_file_path: sourceTxtFilePath,
        output_directory_path: outputDirectoryPath,
        mode,
        chapters_per_file: chaptersPerFile,
        custom_pattern: customPattern,
        title_list: titleList,
        handle_volumes: handleVolumes
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
          "源 TXT 是待切分的整本小说文本，输出目录用于保存切分后的章节文件。",
          "默认模式按内置章节识别规则处理；正则模式使用你提供的表达式；标题列表模式按给定标题切分。",
          "每文件章节数控制合并粒度，分卷处理会尽量保留卷级结构。"
        ]}
      />

      <div className="form-grid form-grid--two">
        <PathInput
          hint="选择要切分的 .txt 文件，也可以拖入文件路径。"
          label="源 TXT"
          onBrowse={() =>
            void pickFile("选择源 TXT", [["文本文件", "*.txt"], ["所有文件", "*.*"]], setSourceTxtFilePath)
          }
          onChange={(event) => setSourceTxtFilePath(event.target.value)}
          onDropPath={setSourceTxtFilePath}
          pathKind="file"
          value={sourceTxtFilePath}
        />
        <PathInput
          hint="切分结果保存到此目录。"
          label="输出目录"
          onBrowse={() => void pickDirectory("选择输出目录", setOutputDirectoryPath)}
          onChange={(event) => setOutputDirectoryPath(event.target.value)}
          onDropPath={setOutputDirectoryPath}
          pathKind="directory"
          value={outputDirectoryPath}
        />
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
