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
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useTaskActions } from "../hooks/useTaskActions";

type SplitterMode = "default" | "regex" | "title_list";

export function SplitterPage() {
  const { startTask } = useTaskActions();
  const { isTaskBusy } = useTaskAvailability();
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
          type="button"
        >
          <Play size={18} />
          <span>开始</span>
        </button>
      </div>

      <div className="form-grid form-grid--two">
        <PathInput
          label="源 TXT"
          onChange={(event) => setSourceTxtFilePath(event.target.value)}
          value={sourceTxtFilePath}
        />
        <PathInput
          label="输出目录"
          onChange={(event) => setOutputDirectoryPath(event.target.value)}
          value={outputDirectoryPath}
        />
        <SelectField
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
          label="正则表达式"
          onChange={(event) => setCustomPattern(event.target.value)}
          value={customPattern}
        />
      ) : null}

      {mode === "title_list" ? (
        <TextAreaField
          label="标题列表"
          onChange={(event) => setTitleListText(event.target.value)}
          value={titleListText}
        />
      ) : null}
    </section>
  );
}
