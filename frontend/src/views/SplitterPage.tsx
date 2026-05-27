import { Eye, FolderOpen, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import type { ChapterPreviewItem } from "../api/types";
import { PatternSelector } from "../components/patterns/PatternSelector";
import { SplitPreviewPanel } from "../components/splitting/SplitPreviewPanel";
import {
  SelectField,
  TextAreaField,
  ToggleSwitch,
} from "../components/forms/FormControls";
import { GuidancePanel } from "../components/common/Guidance";
import { usePathPicker } from "../hooks/usePathPicker";
import { useTaskAvailability } from "../hooks/useTaskAvailability";

type SplitterMode = "default" | "regex" | "title_list";

function readFileContent(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const buf = reader.result as ArrayBuffer;
      const utf8 = new TextDecoder("utf-8", { fatal: false }).decode(buf);
      if (!utf8.includes("�") && !utf8.includes("\0")) {
        resolve(utf8);
        return;
      }
      try {
        resolve(new TextDecoder("gbk", { fatal: true }).decode(buf));
      } catch {
        resolve(utf8);
      }
    };
    reader.onerror = () => reject(new Error("读取文件失败"));
    reader.readAsArrayBuffer(file);
  });
}

export function SplitterPage() {
  const { isTaskBusy } = useTaskAvailability();
  const { pickDirectory } = usePathPicker();

  const [mode, setMode] = useState<SplitterMode>("default");
  const [handleVolumes, setHandleVolumes] = useState(true);
  const [selectedPatternId, setSelectedPatternId] = useState("");
  const [titleListText, setTitleListText] = useState("");
  const [outputDirectory, setOutputDirectory] = useState("");

  // 源文件
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [sourceContent, setSourceContent] = useState("");

  // 预览
  const [previewChapters, setPreviewChapters] = useState<ChapterPreviewItem[] | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  // 执行
  const [running, setRunning] = useState(false);
  const [resultMessage, setResultMessage] = useState("");

  // 拖放
  const [isDragging, setIsDragging] = useState(false);

  const titleList = titleListText
    .split(/\r?\n/)
    .map((t) => t.trim())
    .filter(Boolean);

  const canStart =
    sourceFile != null &&
    (mode !== "regex" || selectedPatternId.length > 0) &&
    (mode !== "title_list" || titleList.length > 0) &&
    outputDirectory.length > 0 &&
    !isTaskBusy && !running;

  const canPreview = canStart && !previewLoading;

  // 模式/参数切换时清除预览
  useEffect(() => {
    setPreviewChapters(null);
    setPreviewError("");
  }, [mode, selectedPatternId, handleVolumes, titleListText]);

  // 上传源文件
  const handleFileSelect = async (fileList: FileList | File[]) => {
    const files = Array.from(fileList);
    if (files.length === 0) return;
    setResultMessage("");
    setPreviewChapters(null);
    setPreviewError("");
    try {
      const file = files[0];
      setSourceFile(file);
      const content = await readFileContent(file);
      setSourceContent(content);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "读取文件失败");
    }
  };

  // 预览
  const previewSplit = async () => {
    if (!sourceContent) return;
    setPreviewChapters(null);
    setPreviewError("");
    setPreviewLoading(true);
    try {
      const result = await apiClient.previewSplit({
        file_content: sourceContent,
        mode,
        pattern_config_id: mode === "regex" ? selectedPatternId : undefined,
        title_list: mode === "title_list" ? titleList : undefined,
        handle_volumes: handleVolumes,
      });
      setPreviewChapters(result.chapters);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "预览失败");
    } finally {
      setPreviewLoading(false);
    }
  };

  // 直接分割
  const doSplit = async () => {
    if (!sourceContent) return;
    setRunning(true);
    setResultMessage("");
    try {
      const result = await apiClient.directSplit({
        file_content: sourceContent,
        output_directory_path: outputDirectory,
        mode,
        pattern_config_id: mode === "regex" ? selectedPatternId : undefined,
        title_list: mode === "title_list" ? titleList : undefined,
        handle_volumes: handleVolumes,
      });
      setResultMessage(`分割完成，共生成 ${result.file_count} 个章节文件`);
      setSourceFile(null);
      setSourceContent("");
      setPreviewChapters(null);
    } catch (err) {
      setResultMessage(err instanceof Error ? `分割失败：${err.message}` : "分割失败");
    } finally {
      setRunning(false);
    }
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
          onClick={() => { void doSplit(); }}
          title="开始分割"
          type="button"
        >
          <Play size={18} />
          <span>开始</span>
        </button>
      </div>

      <GuidancePanel
        title="章节分割流程"
        items={[
          "纯工具：选择源文件 → 配置分割规则 → 选择输出目录 → 开始分割。不创建项目、不暂存文件。",
          "默认模式按内置章节识别规则处理；正则模式使用配置管理器中的表达式；标题列表模式按给定标题切分。",
          "建议先「预览分割」确认匹配结果，无误后再「开始」分割。",
          "分卷处理仅对默认和正则模式生效，可保留卷级顺序。"
        ]}
      />

      <section className="config-card">
        <header className="config-card__header">
          <h3>源文件</h3>
        </header>

        <div
            className={`upload-field file-list-field ${isDragging ? "upload-field--dragging" : ""}`}
            onDragLeave={() => setIsDragging(false)}
            onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; setIsDragging(true); }}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleFileSelect(e.dataTransfer.files); }}
          >
          <header className="file-list-header">
            <span className="file-list-title">
              <span className="field-label">选择 TXT 文件</span>
              {sourceFile ? <span className="field-hint">{sourceFile.name}</span> : null}
            </span>
            {sourceFile ? (
              <button
                className="secondary-command secondary-command--compact"
                onClick={() => { setSourceFile(null); setSourceContent(""); }}
                type="button"
              >
                清除
              </button>
            ) : null}
          </header>
          {!sourceFile ? (
            <label className="upload-command">
              <span>拖拽 .txt 文件到此处或点击选择</span>
              <input
                accept=".txt"
                className="upload-input"
                onChange={(e) => { if (e.target.files) handleFileSelect(e.target.files); e.target.value = ""; }}
                type="file"
              />
            </label>
          ) : null}
        </div>
      </section>

      <div className="form-grid form-grid--two">
        <SelectField
          hint="决定章节边界的识别方式。"
          label="分割模式"
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
        {mode !== "title_list" ? (
          <ToggleSwitch checked={handleVolumes} label="分卷处理" onChange={setHandleVolumes} />
        ) : null}
      </section>

      {mode === "regex" ? (
        <PatternSelector configId={selectedPatternId} onChange={setSelectedPatternId} />
      ) : null}

      {mode === "title_list" ? (
        <TextAreaField
          hint="每行一个章节标题，按列表顺序进行匹配。"
          label="标题列表"
          onChange={(event) => setTitleListText(event.target.value)}
          value={titleListText}
        />
      ) : null}

      <section className="config-card">
        <header className="config-card__header">
          <h3>输出目录</h3>
        </header>
        <div className="field-shell">
          <span className="field-hint">分割后的章节 .txt 文件将写入此目录。</span>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              className="text-control"
              onChange={(e) => setOutputDirectory(e.target.value)}
              placeholder="选择输出目录..."
              readOnly
              style={{ flex: 1, width: "auto" }}
              value={outputDirectory}
            />
            <button
              className="secondary-command"
              onClick={() => { void pickDirectory("选择输出目录", setOutputDirectory); }}
              style={{ flexShrink: 0 }}
              type="button"
            >
              浏览...
            </button>
            {outputDirectory ? (
              <button
                className="icon-button"
                onClick={() => { void apiClient.openDirectory({ path: outputDirectory }); }}
                style={{ flexShrink: 0 }}
                title="打开目录"
                type="button"
              >
                <FolderOpen size={16} />
              </button>
            ) : null}
          </div>
        </div>
      </section>

      <div className="split-source-actions">
        <button
          className="secondary-command"
          disabled={!canPreview}
          onClick={() => { void previewSplit(); }}
          type="button"
        >
          <Eye size={16} />
          <span>预览分割</span>
        </button>
      </div>

      <SplitPreviewPanel
        chapters={previewChapters}
        loading={previewLoading}
        error={previewError}
        onConfirm={() => { void doSplit(); }}
        onCancel={() => setPreviewChapters(null)}
      />

      {resultMessage ? (
        <span className={`field-hint ${resultMessage.includes("失败") ? "field-hint--warning" : ""}`}>
          {resultMessage}
        </span>
      ) : null}
    </section>
  );
}
