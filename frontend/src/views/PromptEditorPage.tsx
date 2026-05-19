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
import type {
  PromptMessage,
  PromptModule,
  PromptNode,
  PromptRole,
  PromptWorkflow,
  WorkflowPromptConfig
} from "../api/types";
import { GuidancePanel } from "../components/common/Guidance";
import { SelectField, TextAreaField, TextInput } from "../components/forms/FormControls";
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

function createEmptyModule(existingModules: PromptModule[]): PromptModule {
  const usedIds = new Set(existingModules.map((module) => module.id));
  let index = existingModules.length + 1;
  let id = `module_${index}`;
  while (usedIds.has(id)) {
    index += 1;
    id = `module_${index}`;
  }
  return {
    id,
    name: `模块 ${index}`,
    description: "",
    content: "",
    default_content: ""
  };
}

function moduleReferenceToken(moduleId: string) {
  return `{{module:${moduleId}}}`;
}

function moduleUsageText(config: WorkflowPromptConfig | null, moduleId: string) {
  if (!config) {
    return "未加载";
  }
  const token = moduleReferenceToken(moduleId);
  const usedNodes = new Set<string>();
  config.workflows.forEach((workflow) => {
    workflow.nodes.forEach((node) => {
      if (node.messages.some((message) => message.content.includes(token))) {
        usedNodes.add(node.title);
      }
    });
  });
  return usedNodes.size ? `被 ${Array.from(usedNodes).join("、")} 引用` : "暂无引用";
}

function comparableModule(module: PromptModule) {
  const { is_dirty: _isDirty, ...rest } = module;
  return rest;
}

export function PromptEditorPage() {
  const { state, dispatch } = useAppState();
  const config = state.workflowPromptConfig;
  const workflows = config?.workflows ?? [];
  const [selectedWorkflowId, setSelectedWorkflowId] = useState("");
  const [selectedNodeKey, setSelectedNodeKey] = useState("");
  const [selectedMessageIndex, setSelectedMessageIndex] = useState(0);
  const [selectedModuleId, setSelectedModuleId] = useState("");
  const [moduleDraft, setModuleDraft] = useState<PromptModule | null>(null);
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
  const selectedModule = useMemo(
    () =>
      config?.modules.find((module) => module.id === selectedModuleId) ??
      (!selectedModuleId ? config?.modules[0] : undefined),
    [config?.modules, selectedModuleId]
  );
  const isModuleDirty = Boolean(
    selectedModule &&
      moduleDraft &&
      JSON.stringify(comparableModule(moduleDraft)) !==
        JSON.stringify(comparableModule(selectedModule))
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
    setSelectedMessageIndex(0);
  }, [selectedNode?.prompt_key]);

  useEffect(() => {
    if (selectedModule && !selectedModuleId) {
      setSelectedModuleId(selectedModule.id);
    }
  }, [selectedModule, selectedModuleId]);

  useEffect(() => {
    setModuleDraft(selectedModule ? { ...selectedModule } : null);
  }, [selectedModule?.id]);

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
    setSelectedMessageIndex(0);
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

  const applyPromptConfig = (nextConfig: WorkflowPromptConfig) => {
    dispatch({ type: "set_workflow_prompt_config", config: nextConfig });
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

  const addModule = () => {
    const nextModule = createEmptyModule(config?.modules ?? []);
    setSelectedModuleId(nextModule.id);
    setModuleDraft(nextModule);
  };

  const updateModuleDraft = <K extends keyof PromptModule>(
    key: K,
    value: PromptModule[K]
  ) => {
    setModuleDraft((current) => (current ? { ...current, [key]: value } : current));
  };

  const saveModule = async () => {
    if (!moduleDraft) {
      return;
    }
    try {
      const savedConfig = await apiClient.savePromptModule(moduleDraft);
      applyPromptConfig(savedConfig);
      setSelectedModuleId(moduleDraft.id);
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      dispatch({
        type: "set_error",
        message: error instanceof Error ? error.message : String(error)
      });
    }
  };

  const deleteModule = async () => {
    if (!moduleDraft) {
      return;
    }
    try {
      const savedConfig = await apiClient.deletePromptModule(moduleDraft.id);
      applyPromptConfig(savedConfig);
      setSelectedModuleId(savedConfig.modules[0]?.id ?? "");
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      dispatch({
        type: "set_error",
        message: error instanceof Error ? error.message : String(error)
      });
    }
  };

  const insertModuleReference = () => {
    if (!moduleDraft) {
      return;
    }
    const token = moduleReferenceToken(moduleDraft.id);
    setDraftMessages((current) =>
      current.map((message, index) => {
        if (index !== selectedMessageIndex) {
          return message;
        }
        const separator = message.content && !message.content.endsWith("\n") ? "\n" : "";
        return { ...message, content: `${message.content}${separator}${token}` };
      })
    );
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
            title="把当前节点恢复为默认消息"
            type="button"
          >
            <RotateCcw size={17} />
            <span>重置节点</span>
          </button>
          <button
            className="primary-command"
            disabled={!selectedNode || !isDraftDirty}
            onClick={saveNode}
            title="保存当前节点的消息顺序、角色和内容"
            type="button"
          >
            <Save size={17} />
            <span>保存节点</span>
          </button>
        </div>
      </div>

      <GuidancePanel
        title="提示词编排"
        items={[
          "先选择工作流，再选择该工作流中的提示词节点；节点保存后会影响后续任务运行。",
          "每条消息都会按当前顺序发送给模型，角色用于区分系统约束、用户输入和助手示例。",
          "模块可用 {{module:模块ID}} 引用，保存模块后所有引用它的节点都会使用最新内容。"
        ]}
      />

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
        <>
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
                          hint="system 用于全局约束，user 用于任务内容，assistant 可作为示例回复。"
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
                        hint="可使用节点变量，也可以插入 {{module:模块ID}} 引用模块。"
                        label="内容"
                        onFocus={() => setSelectedMessageIndex(index)}
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
        <section className="prompt-module-panel">
          <header className="prompt-node-header">
            <div>
              <h3>提示词模块</h3>
              <span>{config?.modules.length ?? 0} 个模块</span>
            </div>
            <div className="command-row">
              <button className="secondary-command" onClick={addModule} type="button">
                <Plus size={16} />
                <span>新增模块</span>
              </button>
              <button
                className="primary-command"
                disabled={!moduleDraft || (!isModuleDirty && Boolean(selectedModule))}
                onClick={saveModule}
                type="button"
              >
                <Save size={16} />
                <span>保存模块</span>
              </button>
            </div>
          </header>
          <GuidancePanel
            title="模块用法"
            items={[
              "模块适合保存通用输出规则、风格要求或反复使用的约束。",
              "点击“插入引用”会把当前模块引用追加到正在编辑的消息中。",
              "删除仍被节点引用的模块会被后端拒绝，以免任务运行时丢失内容。"
            ]}
          />
          {moduleDraft ? (
            <div className="prompt-module-grid">
              <aside className="prompt-node-list" aria-label="提示词模块列表">
                {config?.modules.map((module) => (
                  <button
                    aria-current={module.id === moduleDraft.id ? "true" : undefined}
                    className="prompt-node-button"
                    key={module.id}
                    onClick={() => setSelectedModuleId(module.id)}
                    type="button"
                  >
                    <span>{module.name}</span>
                    <small>{moduleUsageText(config, module.id)}</small>
                  </button>
                ))}
              </aside>
              <div className="prompt-module-editor">
                <div className="form-grid form-grid--two">
                  <TextInput
                    hint="引用时使用该 ID；建议只用英文、数字、下划线或短横线。"
                    label="模块 ID"
                    onChange={(event) => updateModuleDraft("id", event.target.value)}
                    value={moduleDraft.id}
                  />
                  <TextInput
                    hint="用于在模块列表中辨认模块。"
                    label="模块名称"
                    onChange={(event) => updateModuleDraft("name", event.target.value)}
                    value={moduleDraft.name}
                  />
                </div>
                <TextInput
                  hint="简短描述模块用途。"
                  label="说明"
                  onChange={(event) => updateModuleDraft("description", event.target.value)}
                  value={moduleDraft.description}
                />
                <TextAreaField
                  hint="会在运行时展开到引用它的提示词消息中。"
                  label="模块内容"
                  onChange={(event) => updateModuleDraft("content", event.target.value)}
                  value={moduleDraft.content}
                />
                <div className="command-row">
                  <button
                    className="secondary-command"
                    disabled={!draftMessages.length}
                    onClick={insertModuleReference}
                    type="button"
                  >
                    <Plus size={16} />
                    <span>插入引用</span>
                  </button>
                  <button className="danger-command" onClick={deleteModule} type="button">
                    <Trash2 size={16} />
                    <span>删除模块</span>
                  </button>
                  <span className="field-hint">
                    {moduleUsageText(config, moduleDraft.id)} · 引用格式 {moduleReferenceToken(moduleDraft.id)}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <span className="empty-state">暂无提示词模块。</span>
          )}
        </section>
        </>
      ) : (
        <span className="empty-state">提示词配置尚未加载。</span>
      )}
    </section>
  );
}
