import {
  ArrowDown,
  ArrowUp,
  Layers,
  Plus,
  RotateCcw,
  Save,
  Trash2
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { PromptMessage, PromptNode, PromptRole, PromptWorkflow } from "../api/types";
import { SelectField, TextAreaField } from "../components/forms/FormControls";
import { useAppState } from "../state/AppState";

const roleOptions: Array<{ label: string; value: PromptRole }> = [
  { label: "系统", value: "system" },
  { label: "用户", value: "user" },
  { label: "助手", value: "assistant" }
];

function cloneMessages(messages: PromptMessage[]) {
  return messages.map((message) => ({ ...message }));
}

function nodeStatus(node: PromptNode) {
  return node.is_dirty ? "已修改" : "默认";
}

function workflowNodeCount(workflow: PromptWorkflow) {
  return `${workflow.nodes.length} 个节点`;
}

function replacePromptNode(
  workflows: PromptWorkflow[],
  nextNode: PromptNode
): PromptWorkflow[] {
  return workflows.map((workflow) => ({
    ...workflow,
    nodes: workflow.nodes.map((node) =>
      node.prompt_key === nextNode.prompt_key ? nextNode : node
    )
  }));
}

export function PromptEditorPage() {
  const { state, dispatch } = useAppState();
  const config = state.workflowPromptConfig;
  const workflows = config?.workflows ?? [];
  const [selectedWorkflowId, setSelectedWorkflowId] = useState("");
  const [selectedNodeKey, setSelectedNodeKey] = useState("");
  const [draftMessages, setDraftMessages] = useState<PromptMessage[]>([]);
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
  const isDraftDirty = Boolean(
    selectedNode && JSON.stringify(draftMessages) !== JSON.stringify(selectedNode.messages)
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

  useEffect(() => {
    setDraftMessages(selectedNode ? cloneMessages(selectedNode.messages) : []);
  }, [selectedNode?.prompt_key]);

  const addMessage = () => {
    setDraftMessages((current) => [
      ...current,
      {
        id: `message_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        role: "user",
        content: ""
      }
    ]);
  };

  const updateMessage = <K extends keyof PromptMessage>(
    index: number,
    key: K,
    value: PromptMessage[K]
  ) => {
    setDraftMessages((current) =>
      current.map((message, messageIndex) =>
        messageIndex === index ? { ...message, [key]: value } : message
      )
    );
  };

  const removeMessage = (index: number) => {
    setDraftMessages((current) => current.filter((_, messageIndex) => messageIndex !== index));
  };

  const moveMessage = (index: number, direction: -1 | 1) => {
    setDraftMessages((current) => {
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= current.length) {
        return current;
      }
      const next = [...current];
      [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
      return next;
    });
  };

  const applySavedNode = (node: PromptNode) => {
    if (!config) {
      return;
    }
    dispatch({
      type: "set_workflow_prompt_config",
      config: {
        ...config,
        source: "structured",
        workflows: replacePromptNode(config.workflows, node)
      }
    });
    setDraftMessages(cloneMessages(node.messages));
  };

  const saveNode = async () => {
    if (!selectedNode) {
      return;
    }
    try {
      const saved = await apiClient.savePromptNode(selectedNode.prompt_key, draftMessages);
      applySavedNode(saved);
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      dispatch({
        type: "set_error",
        message: error instanceof Error ? error.message : String(error)
      });
    }
  };

  const resetNode = async () => {
    if (!selectedNode) {
      return;
    }
    try {
      const reset = await apiClient.resetPromptNode(selectedNode.prompt_key);
      applySavedNode(reset);
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      dispatch({
        type: "set_error",
        message: error instanceof Error ? error.message : String(error)
      });
    }
  };

  return (
    <section className="workflow-view">
      <div className="view-header">
        <div>
          <h2>提示词</h2>
          <span>
            {config ? `${workflows.length} 个工作流 · ${config.source}` : "未加载"}
          </span>
        </div>
        <div className="command-row">
          <button
            className="secondary-command"
            disabled={!selectedNode}
            onClick={resetNode}
            type="button"
          >
            <RotateCcw size={17} />
            <span>重置节点</span>
          </button>
          <button
            className="primary-command"
            disabled={!selectedNode || !isDraftDirty}
            onClick={saveNode}
            type="button"
          >
            <Save size={17} />
            <span>保存节点</span>
          </button>
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
                  {isDraftDirty ? <span className="status-pill status-pill--paused">未保存</span> : null}
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
                  <div className="command-row">
                    <button className="secondary-command" onClick={addMessage} type="button">
                      <Plus size={16} />
                      <span>新增消息</span>
                    </button>
                  </div>
                  {draftMessages.map((message, index) => (
                    <section className="prompt-message-card" key={message.id || index}>
                      <header className="prompt-message-header">
                        <SelectField
                          label={`消息 ${index + 1} 角色`}
                          onChange={(event) =>
                            updateMessage(index, "role", event.target.value as PromptRole)
                          }
                          options={roleOptions}
                          value={message.role}
                        />
                        <div className="command-row">
                          <button
                            className="secondary-command secondary-command--compact"
                            disabled={index === 0}
                            onClick={() => moveMessage(index, -1)}
                            title="上移消息"
                            type="button"
                          >
                            <ArrowUp size={16} />
                          </button>
                          <button
                            className="secondary-command secondary-command--compact"
                            disabled={index === draftMessages.length - 1}
                            onClick={() => moveMessage(index, 1)}
                            title="下移消息"
                            type="button"
                          >
                            <ArrowDown size={16} />
                          </button>
                          <button
                            className="danger-command"
                            disabled={draftMessages.length <= 1}
                            onClick={() => removeMessage(index)}
                            title="删除消息"
                            type="button"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </header>
                      <TextAreaField
                        label="内容"
                        onChange={(event) => updateMessage(index, "content", event.target.value)}
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
