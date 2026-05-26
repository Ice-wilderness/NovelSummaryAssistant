import { X } from "lucide-react";
import type { ScanFinding, TriggerScanContextResponse } from "../../api/types";
import { classNames, pathName } from "./display";

export interface ContextState {
  finding: ScanFinding;
  response: TriggerScanContextResponse | null;
  isLoading: boolean;
  error: string;
}

interface ContextModalProps {
  contextState: ContextState;
  onClose: () => void;
}

export function ContextModal({ contextState, onClose }: ContextModalProps) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="context-modal" role="dialog" aria-modal="true">
        <header className="context-modal__header">
          <div>
            <h3>{contextState.finding.rule_name}</h3>
            <span>
              {pathName(contextState.finding.chapter_file)} ·{" "}
              {contextState.finding.paragraph_ids.join(", ")}
            </span>
          </div>
          <button className="icon-button" onClick={onClose} type="button">
            <X size={18} />
          </button>
        </header>
        <div className="context-modal__body">
          {contextState.isLoading ? (
            <span className="empty-state">上下文加载中</span>
          ) : contextState.error ? (
            <span className="field-hint field-hint--warning">{contextState.error}</span>
          ) : contextState.response?.warning ? (
            <span className="field-hint field-hint--warning">
              {contextState.response.warning}
            </span>
          ) : (
            <div className="context-paragraph-list">
              {(contextState.response?.paragraphs ?? []).map((paragraph) => (
                <p
                  className={classNames("context-paragraph", paragraph.matched && "context-paragraph--matched")}
                  key={paragraph.id}
                >
                  <strong>{paragraph.id}</strong>
                  <span>{paragraph.text}</span>
                </p>
              ))}
              {contextState.response?.missing_paragraph_ids?.length ? (
                <span className="field-hint field-hint--warning">
                  缺失段落：{contextState.response.missing_paragraph_ids.join(", ")}
                </span>
              ) : null}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
