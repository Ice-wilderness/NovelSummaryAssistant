import { Play } from "lucide-react";
import { useState } from "react";
import { apiClient } from "../api/client";
import { defaultArticleWordCounts } from "../api/defaults";
import type { ArticleWordCounts } from "../api/types";
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
          type="button"
        >
          <Play size={18} />
          <span>开始</span>
        </button>
      </div>

      <div className="form-grid form-grid--two">
        <PathInput
          label="文章目录"
          onBrowse={() => void pickDirectory("选择文章目录", setSourceFolderPath)}
          onChange={(event) => setSourceFolderPath(event.target.value)}
          onDropPath={setSourceFolderPath}
          value={sourceFolderPath}
        />
        <TextInput
          label="输出子目录"
          onChange={(event) => setOutputSubfolder(event.target.value)}
          value={outputSubfolder}
        />
      </div>

      <TextAreaField
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
