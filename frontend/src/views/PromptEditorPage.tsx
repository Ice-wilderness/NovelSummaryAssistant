import {
  ArrowDown,
  ArrowUp,
  Blocks,
  MessageSquareText,
  Plus,
  RotateCcw,
  Save,
  Trash2,
  Workflow as WorkflowIcon
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
import { StudioMotionSurface, StudioStatusBadge } from "../components/studio/StudioPrimitives";
import { useAppState } from "../state/AppState";

const roleOptions: Array<{ label: string; value: PromptRole }> = [
  { label: "系统", value: "system" },
  { label: "用户", value: "user" },
  { label: "助手", value: "assistant" }
];

function normaliseMessages(
  messages: PromptMessage[] | undefined,
  fallbackContent = "",
  prefix = "message"
) {
  if (Array.isArray(messages) && messages.length > 0) {
    return messages.map((message, index) => ({
      id: message.id || `${prefix}_${index + 1}`,
      kind: message.kind ?? (message.module_id ? "module" : "message"),
      role: message.role ?? "user",
      content: message.content ?? "",
      module_id: message.module_id ?? ""
    }));
  }
  return [
    {
      id: `${prefix}_1`,
      kind: "message" as const,
      role: "user" as const,
      content: fallbackContent,
      module_id: ""
    }
  ];
}

function cloneMessages(
  messages: PromptMessage[] | undefined,
  fallbackContent = "",
  prefix = "message"
) {
  return normaliseMessages(messages, fallbackContent, prefix).map((message) => ({ ...message }));
}

function createEmptyMessage(prefix = "message"): PromptMessage {
  return {
    id: `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    kind: "message",
    role: "user",
    content: "",
    module_id: ""
  };
}

function nodeStatus(node: PromptNode) {
  if (node.runtime_status === "deterministic") {
    return "本地规则";
  }
  return node.is_dirty ? "已修改" : "默认";
}

function nodeRuntimeLabel(node: PromptNode) {
  return node.runtime_status === "deterministic" ? "不调用 LLM" : "LLM 节点";
}

function canEditPromptNode(node: PromptNode | undefined) {
  return Boolean(node && node.runtime_status !== "deterministic");
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
    default_content: "",
    messages: [createEmptyMessage(`${id}_message`)],
    default_messages: []
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
      if (
        node.messages.some(
          (message) =>
            message.module_id === moduleId ||
            (message.kind !== "module" && message.content.includes(token))
        )
      ) {
        usedNodes.add(node.title);
      }
    });
  });
  return usedNodes.size ? `被 ${Array.from(usedNodes).join("、")} 引用` : "";
}

function comparableModule(module: PromptModule) {
  const { is_dirty: _isDirty, ...rest } = module;
  return rest;
}

function moduleContent(messages: PromptMessage[] | undefined) {
  return (messages ?? [])
    .filter((message) => message.kind !== "module")
    .map((message) => message.content)
    .join("\n\n");
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
  const selectedNodeEditable = canEditPromptNode(selectedNode);
  const isDraftDirty = Boolean(
    selectedNodeEditable &&
      selectedNode &&
      JSON.stringify(draftMessages) !== JSON.stringify(selectedNode.messages)
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
  const editableNodeCount = selectedWorkflow?.nodes.filter(canEditPromptNode).length ?? 0;
  const dirtyCount = Number(isDraftDirty) + Number(isModuleDirty);

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
    setDraftMessages(
      selectedNode ? cloneMessages(selectedNode.messages, "", selectedNode.prompt_key) : []
    );
    setSelectedMessageIndex(0);
  }, [selectedNode?.prompt_key]);

  useEffect(() => {
    if (selectedModule && !selectedModuleId) {
      setSelectedModuleId(selectedModule.id);
    }
  }, [selectedModule, selectedModuleId]);

  useEffect(() => {
    if (selectedModule) {
      setModuleDraft({
        ...selectedModule,
        messages: cloneMessages(
          selectedModule.messages,
          selectedModule.content,
          `${selectedModule.id}_message`
        ),
        default_messages: cloneMessages(
          selectedModule.default_messages,
          selectedModule.default_content,
          `${selectedModule.id}_default`
        )
      });
    } else if (!selectedModuleId) {
      setModuleDraft(null);
    }
  }, [selectedModule?.id, selectedModuleId]);

  const addMessage = () => {
    setDraftMessages((current) => [...current, createEmptyMessage()]);
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
    setDraftMessages(cloneMessages(node.messages, "", node.prompt_key));
  };

  const applyPromptConfig = (nextConfig: WorkflowPromptConfig) => {
    dispatch({ type: "set_workflow_prompt_config", config: nextConfig });
  };

  const saveNode = async () => {
    if (!selectedNode || !selectedNodeEditable) {
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
    if (!selectedNode || !selectedNodeEditable) {
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
      const savedMessages = cloneMessages(moduleDraft.messages);
      const savedContent = moduleContent(savedMessages);
      const savedConfig = await apiClient.savePromptModule({
        ...moduleDraft,
        content: savedContent,
        default_content: selectedModule ? moduleDraft.default_content : savedContent,
        default_messages: selectedModule
          ? moduleDraft.default_messages
          : cloneMessages(savedMessages)
      });
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

  const insertModuleAsMessage = (moduleId: string) => {
    setDraftMessages((current) => {
      const next = [...current];
      const insertAt = Math.min(selectedMessageIndex + 1, next.length);
      next.splice(insertAt, 0, {
        id: `module_ref_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        kind: "module",
        role: "user",
        content: "",
        module_id: moduleId
      });
      setSelectedMessageIndex(insertAt);
      return next;
    });
  };

  const updateModuleMessage = <K extends keyof PromptMessage>(
    index: number,
    key: K,
    value: PromptMessage[K]
  ) => {
    setModuleDraft((current) =>
      current
        ? {
            ...current,
            messages: (current.messages ?? []).map((message, messageIndex) =>
              messageIndex === index ? { ...message, [key]: value } : message
            )
          }
        : current
    );
  };

  const addModuleMessage = () => {
    setModuleDraft((current) =>
      current
        ? {
            ...current,
            messages: [...(current.messages ?? []), createEmptyMessage(`${current.id}_message`)]
          }
        : current
    );
  };

  const removeModuleMessage = (index: number) => {
    setModuleDraft((current) =>
      current
        ? {
            ...current,
            messages: (current.messages ?? []).filter((_, messageIndex) => messageIndex !== index)
          }
        : current
    );
  };

  const moveModuleMessage = (index: number, direction: -1 | 1) => {
    setModuleDraft((current) => {
      if (!current) {
        return current;
      }
      const targetIndex = index + direction;
      const messages = [...(current.messages ?? [])];
      if (targetIndex < 0 || targetIndex >= messages.length) {
        return current;
      }
      [messages[index], messages[targetIndex]] = [messages[targetIndex], messages[index]];
      return { ...current, messages };
    });
  };

  return (
    <section className="workflow-view support-studio prompt-studio">
      <StudioMotionSurface className="support-hero support-hero--prompt">
        <div className="support-hero__copy">
          <span>Prompt Orchestration Studio</span>
          <h2>提示词</h2>
          <p>{selectedNode ? `${selectedWorkflow?.title ?? "工作流"} · ${selectedNode.title}` : "选择工作流后编辑 LLM 节点与复用模块"}</p>
        </div>
        <div className="support-hero__stats">
          <StudioStatusBadge tone={dirtyCount > 0 ? "warning" : "success"}>
            {dirtyCount > 0 ? `${dirtyCount} 处未保存` : "已同步"}
          </StudioStatusBadge>
          <span>{config ? `${workflows.length} 个工作流` : "未加载"}</span>
          <span>{editableNodeCount} 个可编辑节点</span>
          <span>{config?.modules.length ?? 0} 个模块</span>
        </div>
        <div className="command-row support-hero__actions">
          <button
            className="secondary-command"
            disabled={!selectedNodeEditable}
            onClick={resetNode}
            title="把当前节点恢复为默认消息"
            type="button"
          >
            <RotateCcw size={17} />
            <span>重置节点</span>
          </button>
          <button
            className="primary-command"
            disabled={!selectedNodeEditable || !isDraftDirty}
            onClick={saveNode}
            title="保存当前节点的消息顺序、角色和内容"
            type="button"
          >
            <Save size={17} />
            <span>保存节点</span>
          </button>
        </div>
      </StudioMotionSurface>

      <div className="support-flow-guide">
        <GuidancePanel
          title="提示词编排"
          items={[
            "先选择工作流，再选择该工作流中的 LLM 提示词节点；LLM 节点保存后会影响后续任务运行。",
            "每条消息都会按当前顺序发送给模型，角色用于区分系统约束、用户输入和助手示例。",
            "模块会作为节点序列里的独立块插入，运行时按模块内部的角色和顺序展开。"
          ]}
        />
      </div>

      <div className="prompt-tabs prompt-studio-tabs" role="tablist" aria-label="提示词工作流">
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
        <StudioMotionSurface className="prompt-workflow-shell prompt-studio-workflow">
          <aside className="prompt-node-list" aria-label={`${selectedWorkflow.title}提示词节点`}>
            <div className="prompt-section-title">
              <WorkflowIcon size={17} />
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
                    <span><MessageSquareText size={15} /> 节点消息</span>
                    <h3>{selectedNode.title}</h3>
                    <span>{selectedNode.filename || selectedNode.prompt_key}</span>
                  </div>
                  <span className="status-pill">{nodeStatus(selectedNode)}</span>
                  <span
                    className={`status-pill ${
                      selectedNodeEditable ? "status-pill--success" : "status-pill--idle"
                    }`}
                  >
                    {nodeRuntimeLabel(selectedNode)}
                  </span>
                  {isDraftDirty ? <span className="status-pill status-pill--paused">未保存</span> : null}
                </header>
                <p className="prompt-node-description">{selectedNode.description}</p>
                <div className="prompt-meta-grid">
                  {selectedNode.runtime_note ? (
                    <div className="result-panel result-panel--compact">
                      <strong>运行时</strong>
                      <span>{selectedNode.runtime_note}</span>
                    </div>
                  ) : null}
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
                    <button
                      className="secondary-command"
                      disabled={!selectedNodeEditable}
                      onClick={addMessage}
                      type="button"
                    >
                      <Plus size={16} />
                      <span>新增消息</span>
                    </button>
                    <select
                      className="module-ref-select"
                      disabled={!selectedNodeEditable}
                      value=""
                      onChange={(event) => {
                        if (event.target.value) {
                          insertModuleAsMessage(event.target.value);
                          event.target.value = "";
                        }
                      }}
                    >
                      <option value="">插入模块引用...</option>
                      {(config?.modules ?? []).map((module) => (
                        <option key={module.id} value={module.id}>
                          {module.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  {draftMessages.map((message, index) => (
                    <section
                      className="prompt-message-card"
                      key={message.id || index}
                      onClick={() => setSelectedMessageIndex(index)}
                    >
                      <header className="prompt-message-header">
                        {message.kind === "module" ? (
                          <SelectField
                            hint="模块引用会在运行时展开为该模块内部的有序角色消息。"
                            label={`位置 ${index + 1} 模块`}
                            disabled={!selectedNodeEditable}
                            onChange={(event) =>
                              updateMessage(index, "module_id", event.target.value)
                            }
                            options={(config?.modules ?? []).map((module) => ({
                              label: module.name,
                              value: module.id
                            }))}
                            value={message.module_id ?? ""}
                          />
                        ) : (
                          <SelectField
                            hint="system 用于全局约束，user 用于任务内容，assistant 可作为示例回复。"
                            label={`消息 ${index + 1} 角色`}
                            disabled={!selectedNodeEditable}
                            onChange={(event) =>
                              updateMessage(index, "role", event.target.value as PromptRole)
                            }
                            options={roleOptions}
                            value={message.role}
                          />
                        )}
                        <div className="command-row">
                          <button
                            className="secondary-command secondary-command--compact"
                            disabled={!selectedNodeEditable || index === 0}
                            onClick={() => moveMessage(index, -1)}
                            title="上移消息"
                            type="button"
                          >
                            <ArrowUp size={16} />
                          </button>
                          <button
                            className="secondary-command secondary-command--compact"
                            disabled={!selectedNodeEditable || index === draftMessages.length - 1}
                            onClick={() => moveMessage(index, 1)}
                            title="下移消息"
                            type="button"
                          >
                            <ArrowDown size={16} />
                          </button>
                          <button
                            className="danger-command"
                            disabled={!selectedNodeEditable || draftMessages.length <= 1}
                            onClick={() => removeMessage(index)}
                            title="删除消息"
                            type="button"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </header>
                      {message.kind === "module" ? (
                        <div className="result-panel result-panel--compact">
                          <strong>模块块</strong>
                          <span>
                            {message.module_id
                              ? (config?.modules.find((m) => m.id === message.module_id)?.name ?? message.module_id)
                              : "请选择模块"}
                          </span>
                        </div>
                      ) : (
                        <TextAreaField
                          hint={"可使用节点变量；模块引用请通过上方“插入模块引用”下拉选择加入。"}
                          label="内容"
                          disabled={!selectedNodeEditable}
                          onFocus={() => setSelectedMessageIndex(index)}
                          onChange={(event) => updateMessage(index, "content", event.target.value)}
                          value={message.content}
                        />
                      )}
                    </section>
                  ))}
                </div>
              </>
            ) : (
              <span className="empty-state">请选择一个提示词节点。</span>
            )}
          </div>
        </StudioMotionSurface>
        <StudioMotionSurface className="prompt-module-panel prompt-studio-module-panel">
          <header className="prompt-node-header">
            <div>
              <span><Blocks size={15} /> Reusable Blocks</span>
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
            title={"模块用法"}
            items={[
              "模块适合保存通用输出规则、风格要求或反复使用的约束。",
              "在节点编辑器中，通过“插入模块引用”下拉菜单将模块作为独立块加入消息序列。",
              "删除仍被节点引用的模块会被后端拒绝；模块需插入到节点消息中才会在运行时生效。"
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
                    {moduleUsageText(config, module.id) && (
                      <small>{moduleUsageText(config, module.id)}</small>
                    )}
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
                <section className="prompt-message-preview">
                  <div className="command-row">
                    <button className="secondary-command" onClick={addModuleMessage} type="button">
                      <Plus size={16} />
                      <span>新增模块消息</span>
                    </button>
                  </div>
                  {(moduleDraft.messages ?? []).map((message, index) => (
                    <section className="prompt-message-card" key={message.id || index}>
                      <header className="prompt-message-header">
                        <SelectField
                          hint="模块内部消息会按这里的角色和顺序展开到节点中。"
                          label={`模块消息 ${index + 1} 角色`}
                          onChange={(event) =>
                            updateModuleMessage(index, "role", event.target.value as PromptRole)
                          }
                          options={roleOptions}
                          value={message.role}
                        />
                        <div className="command-row">
                          <button
                            className="secondary-command secondary-command--compact"
                            disabled={index === 0}
                            onClick={() => moveModuleMessage(index, -1)}
                            title="上移模块消息"
                            type="button"
                          >
                            <ArrowUp size={16} />
                          </button>
                          <button
                            className="secondary-command secondary-command--compact"
                            disabled={index === (moduleDraft.messages ?? []).length - 1}
                            onClick={() => moveModuleMessage(index, 1)}
                            title="下移模块消息"
                            type="button"
                          >
                            <ArrowDown size={16} />
                          </button>
                          <button
                            className="danger-command"
                            disabled={(moduleDraft.messages ?? []).length <= 1}
                            onClick={() => removeModuleMessage(index)}
                            title="删除模块消息"
                            type="button"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </header>
                      <TextAreaField
                        hint="模块消息可使用节点提供的变量，运行时会一起格式化。"
                        label="内容"
                        onChange={(event) =>
                          updateModuleMessage(index, "content", event.target.value)
                        }
                        value={message.content}
                      />
                    </section>
                  ))}
                </section>
                <div className="command-row">
                  <button className="danger-command" onClick={deleteModule} type="button">
                    <Trash2 size={16} />
                    <span>删除模块</span>
                  </button>
                  {moduleUsageText(config, moduleDraft.id) && (
                    <span className="field-hint">
                      {moduleUsageText(config, moduleDraft.id)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <span className="empty-state">暂无提示词模块。</span>
          )}
        </StudioMotionSurface>
        </>
      ) : (
        <span className="empty-state">提示词配置尚未加载。</span>
      )}
    </section>
  );
}
