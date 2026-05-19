import { Layers, ScrollText } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { PromptNode, PromptWorkflow } from "../api/types";
import { TextAreaField } from "../components/forms/FormControls";
import { useAppState } from "../state/AppState";

function nodeStatus(node: PromptNode) {
  return node.is_dirty ? "已修改" : "默认";
}

function workflowNodeCount(workflow: PromptWorkflow) {
  return `${workflow.nodes.length} 个节点`;
}

export function PromptEditorPage() {
  const { state } = useAppState();
  const config = state.workflowPromptConfig;
  const workflows = config?.workflows ?? [];
  const [selectedWorkflowId, setSelectedWorkflowId] = useState("");
  const [selectedNodeKey, setSelectedNodeKey] = useState("");
  const selectedWorkflow = useMemo(
    () =>
      workflows.find((workflow) => workflow.id === selectedWorkflowId) ??
      workflows[0],
    [selectedWorkflowId, workflows]
  );
  const selectedNode = useMemo(
    () =>
      selectedWorkflow?.nodes.find((node) => node.prompt_key === selectedNodeKey) ??
      selectedWorkflow?.nodes[0],
    [selectedNodeKey, selectedWorkflow]
  );

  useEffect(() => {
    if (selectedWorkflow && selectedWorkflow.id !== selectedWorkflowId) {
      setSelectedWorkflowId(selectedWorkflow.id);
    }
  }, [selectedWorkflow, selectedWorkflowId]);

  useEffect(() => {
    if (selectedNode && selectedNode.prompt_key !== selectedNodeKey) {
      setSelectedNodeKey(selectedNode.prompt_key);
    }
  }, [selectedNode, selectedNodeKey]);

  return (
    <section className="workflow-view">
      <div className="view-header">
        <div>
          <h2>提示词</h2>
          <span>
            {config ? `${workflows.length} 个工作流 · ${config.source}` : "未加载"}
          </span>
        </div>
      </div>

      <div className="prompt-tabs" role="tablist" aria-label="提示词工作流">
        {workflows.map((workflow) => (
          <button
            aria-selected={workflow.id === selectedWorkflow?.id}
            className="prompt-tab"
            key={workflow.id}
            onClick={() => {
              setSelectedWorkflowId(workflow.id);
              setSelectedNodeKey(workflow.nodes[0]?.prompt_key ?? "");
            }}
            role="tab"
            type="button"
          >
            <span>{workflow.title}</span>
            <small>{workflowNodeCount(workflow)}</small>
          </button>
        ))}
      </div>

      {selectedWorkflow ? (
        <section className="prompt-workflow-shell">
          <aside className="prompt-node-list" aria-label={`${selectedWorkflow.title}提示词节点`}>
            <div className="prompt-section-title">
              <Layers size={17} />
              <strong>{selectedWorkflow.title}</strong>
            </div>
            <p>{selectedWorkflow.description}</p>
            {selectedWorkflow.nodes.length === 0 ? (
              <span className="empty-state">
                {selectedWorkflow.empty_message || "当前工作流没有可编辑提示词节点。"}
              </span>
            ) : (
              selectedWorkflow.nodes.map((node) => (
                <button
                  aria-current={node.prompt_key === selectedNode?.prompt_key ? "true" : undefined}
                  className="prompt-node-button"
                  key={node.prompt_key}
                  onClick={() => setSelectedNodeKey(node.prompt_key)}
                  type="button"
                >
                  <span>{node.title}</span>
                  <small>{nodeStatus(node)}</small>
                </button>
              ))
            )}
          </aside>

          <div className="prompt-editor-panel">
            {selectedNode ? (
              <>
                <header className="prompt-node-header">
                  <div>
                    <h3>{selectedNode.title}</h3>
                    <span>{selectedNode.filename || selectedNode.prompt_key}</span>
                  </div>
                  <span className="status-pill">{nodeStatus(selectedNode)}</span>
                </header>
                <p className="prompt-node-description">{selectedNode.description}</p>
                <div className="prompt-meta-grid">
                  <div className="result-panel result-panel--compact">
                    <strong>变量</strong>
                    <span>
                      {selectedNode.variables.length
                        ? selectedNode.variables.join(", ")
                        : "无变量"}
                    </span>
                  </div>
                  <div className="result-panel result-panel--compact">
                    <strong>消息</strong>
                    <span>{selectedNode.messages.length} 条</span>
                  </div>
                </div>
                <div className="prompt-message-preview">
                  {selectedNode.messages.map((message, index) => (
                    <section className="prompt-message-card" key={message.id || index}>
                      <header>
                        <ScrollText size={16} />
                        <strong>{message.role}</strong>
                      </header>
                      <TextAreaField
                        label={`消息 ${index + 1}`}
                        readOnly
                        value={message.content}
                      />
                    </section>
                  ))}
                </div>
              </>
            ) : (
              <span className="empty-state">请选择一个提示词节点。</span>
            )}
          </div>
        </section>
      ) : (
        <span className="empty-state">提示词配置尚未加载。</span>
      )}
    </section>
  );
}
