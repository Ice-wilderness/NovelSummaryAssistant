import { AlertTriangle, Check, Loader, X } from "lucide-react";
import type { ChapterPreviewItem } from "../../api/types";

interface Props {
  chapters: ChapterPreviewItem[] | null;
  loading: boolean;
  error: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function SplitPreviewPanel({ chapters, loading, error, onConfirm, onCancel }: Props) {
  const errorTitle = error.startsWith("分割失败") ? "分割失败" : "预览失败";

  if (loading) {
    return (
      <div className="split-preview-panel">
        <div className="split-preview-panel__loading">
          <Loader size={20} className="spin" />
          <span style={{ marginLeft: 8 }}>正在预览分割结果...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="split-preview-panel">
        <div className="split-preview-panel__header">
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <AlertTriangle size={16} color="#f87171" />
            <strong>{errorTitle}</strong>
          </span>
          <button className="icon-button" onClick={onCancel} type="button">
            <X size={16} />
          </button>
        </div>
        <div className="split-preview-panel__loading">
          <span className="field-hint field-hint--warning">{error}</span>
        </div>
      </div>
    );
  }

  if (!chapters) {
    return null;
  }

  if (chapters.length === 0) {
    return (
      <div className="split-preview-panel">
        <div className="split-preview-panel__header">
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <AlertTriangle size={16} color="#fbbf24" />
            <strong>未匹配到任何章节</strong>
          </span>
          <button className="icon-button" onClick={onCancel} type="button">
            <X size={16} />
          </button>
        </div>
        <div className="split-preview-panel__loading">
          <span className="field-hint">当前正则未匹配到内容，请检查表达式或切换配置。</span>
        </div>
      </div>
    );
  }

  return (
    <div className="split-preview-panel">
      <div className="split-preview-panel__header">
        <span>
          <strong>分割预览</strong>
          {" · "}
          <span className="count">{chapters.length}</span> 章
          {" · "}
          <span className="count">{(chapters.reduce((s, ch) => s + ch.word_count, 0)).toLocaleString()}</span> 字
        </span>
        <button className="icon-button" onClick={onCancel} type="button">
          <X size={16} />
        </button>
      </div>
      <div className="split-preview-panel__list">
        {chapters.map((ch) => (
          <div
            className={`split-preview-item ${ch.matched === false ? "split-preview-item--unmatched" : ""}`}
            key={ch.index}
          >
            <span className="split-preview-item__index">{ch.index}.</span>
            <span className="split-preview-item__title">{ch.title}</span>
            <span className="split-preview-item__line">
              {ch.word_count > 0 ? `${ch.word_count.toLocaleString()} 字` : ch.line_number > 0 ? `行 ${ch.line_number}` : "未匹配"}
            </span>
          </div>
        ))}
      </div>
      <div className="split-preview-panel__actions">
        <button className="secondary-command" onClick={onCancel} type="button">
          取消
        </button>
        <button className="primary-command" onClick={onConfirm} type="button">
          <Check size={16} />
          <span>确认分割</span>
        </button>
      </div>
    </div>
  );
}
