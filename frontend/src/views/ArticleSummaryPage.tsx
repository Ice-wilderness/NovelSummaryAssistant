import { Play } from "lucide-react";
import { useState } from "react";
import { apiClient } from "../api/client";
import { defaultArticleWordCounts } from "../api/defaults";
import type { ArticleWordCounts } from "../api/types";
import { GuidancePanel } from "../components/common/Guidance";
import { PathInput, TextAreaField, TextInput } from "../components/forms/FormControls";
import { appendImportedPaths, usePathPicker } from "../hooks/usePathPicker";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useTaskActions } from "../hooks/useTaskActions";

export function ArticleSummaryPage() {
  const { startTask } = useTaskActions();
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory } = usePathPicker();
  const [sourceFolderPath, setSourceFolderPath] = useState("");
  const [selectedFilesText, setSelectedFilesText] = useState("");
  const [outputSubfolder, setOutputSubfolder] = useState("");
  const [wordCounts, setWordCounts] = useState<ArticleWordCounts>(defaultArticleWordCounts);

  const selectedFiles = selectedFilesText
    .split(/\r?\n/)
    .map((file) => file.trim())
    .filter(Boolean);

  const updateWordCount = (key: keyof ArticleWordCounts, value: string) => {
    setWordCounts((current) => ({ ...current, [key]: value }));
  };

  const startArticleSummary = () => {
    void startTask(() =>
      apiClient.startArticleSummary({
        source_folder_path: sourceFolderPath,
        selected_files: selectedFiles,
        output_subfolder: outputSubfolder,
        word_counts: wordCounts
      })
    );
  };
  const canStart =
    sourceFolderPath.trim().length > 0 && selectedFiles.length > 0 && !isTaskBusy;

  return (
    <section className="workflow-view">
      <div className="view-header">
        <div>
          <h2>文章总结</h2>
          <span>{selectedFiles.length} 个文件</span>
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
          "文章目录是文件列表的基准目录；文件列表每行一个相对或绝对路径。",
          "段落总结会先处理每个选中文件，最终总结会整合所有段落摘要。",
          "输出子目录为空时使用默认输出位置，字数设置会传入文章提示词变量。"
        ]}
      />

      <div className="form-grid form-grid--two">
        <PathInput
          hint="选择文章文件所在目录，也可以拖入目录路径。"
          label="文章目录"
          onBrowse={() => void pickDirectory("选择文章目录", setSourceFolderPath)}
          onChange={(event) => setSourceFolderPath(event.target.value)}
          onDropPath={setSourceFolderPath}
          pathKind="directory"
          value={sourceFolderPath}
        />
        <TextInput
          hint="可选；填写后结果写入该子目录。"
          label="输出子目录"
          onChange={(event) => setOutputSubfolder(event.target.value)}
          value={outputSubfolder}
        />
      </div>

      <TextAreaField
        hint="每行一个文件路径；支持拖入文件追加到列表。"
        label="文件列表"
        onChange={(event) => setSelectedFilesText(event.target.value)}
        onDropPaths={(paths) =>
          setSelectedFilesText((current) => appendImportedPaths(current, paths))
        }
        value={selectedFilesText}
      />

      <section className="word-count-section">
        <h3>字数设置</h3>
        <div className="word-count-grid word-count-grid--compact">
          <TextInput
            label="段落总结"
            onChange={(event) => updateWordCount("section", event.target.value)}
            value={wordCounts.section}
          />
          <TextInput
            label="最终总结"
            onChange={(event) => updateWordCount("final", event.target.value)}
            value={wordCounts.final}
          />
        </div>
      </section>
    </section>
  );
}
