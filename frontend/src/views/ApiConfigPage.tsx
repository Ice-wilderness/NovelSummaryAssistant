import { Eye, EyeOff, Plus, RefreshCw, Save, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { ApiConfig } from "../api/types";
import { NumberInput, TextInput, ToggleSwitch } from "../components/forms/FormControls";
import { useAppState } from "../state/AppState";

function createEmptyApiConfig(): ApiConfig {
  return {
    id: `api_${Date.now()}`,
    url: "",
    key: "",
    model: "",
    max_tokens: 4096,
    temperature: 0.7,
    stream: true,
    timeout: 180,
    max_retries: 3,
    is_active: true,
    key_env_var: "",
    has_key: false,
    has_env_key: false
  };
}

export function ApiConfigPage() {
  const { state, dispatch } = useAppState();
  const [drafts, setDrafts] = useState<ApiConfig[]>([]);
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});
  const [modelOptions, setModelOptions] = useState<Record<string, string[]>>({});
  const [statusText, setStatusText] = useState("");
  const isDirty = useMemo(
    () => JSON.stringify(drafts) !== JSON.stringify(state.apiConfigs),
    [drafts, state.apiConfigs]
  );

  useEffect(() => {
    setDrafts(state.apiConfigs);
  }, [state.apiConfigs]);

  const updateDraft = <K extends keyof ApiConfig>(
    index: number,
    key: K,
    value: ApiConfig[K]
  ) => {
    setDrafts((current) =>
      current.map((config, itemIndex) =>
        itemIndex === index ? { ...config, [key]: value } : config
      )
    );
  };

  const addConfig = () => {
    setDrafts((current) => [...current, createEmptyApiConfig()]);
  };

  const removeConfig = (index: number) => {
    setDrafts((current) => current.filter((_, itemIndex) => itemIndex !== index));
  };

  const reloadConfigs = async () => {
    try {
      const configs = await apiClient.loadApiConfigs();
      dispatch({ type: "set_api_configs", items: configs });
      dispatch({ type: "set_error", message: null });
      setStatusText("已重新加载");
    } catch (error: unknown) {
      dispatch({
        type: "set_error",
        message: error instanceof Error ? error.message : String(error)
      });
    }
  };

  const saveConfigs = async () => {
    try {
      const saved = await apiClient.saveApiConfigs(drafts);
      dispatch({ type: "set_api_configs", items: saved });
      dispatch({ type: "set_error", message: null });
      setStatusText("已保存");
    } catch (error: unknown) {
      dispatch({
        type: "set_error",
        message: error instanceof Error ? error.message : String(error)
      });
    }
  };

  const fetchModels = async (config: ApiConfig) => {
    try {
      const models = await apiClient.fetchModels(config);
      setModelOptions((current) => ({ ...current, [config.id]: models }));
      dispatch({ type: "set_error", message: null });
      setStatusText(`已获取 ${models.length} 个模型`);
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
          <h2>API 配置</h2>
          <span>{statusText || `${drafts.length} 个配置`}</span>
        </div>
        <div className="command-row">
          <button className="secondary-command" onClick={reloadConfigs} type="button">
            <RefreshCw size={17} />
            <span>加载</span>
          </button>
          <button className="secondary-command" onClick={addConfig} type="button">
            <Plus size={17} />
            <span>新增</span>
          </button>
          <button
            className="primary-command"
            disabled={!isDirty}
            onClick={saveConfigs}
            type="button"
          >
            <Save size={17} />
            <span>保存</span>
          </button>
        </div>
      </div>

      <div className="config-list">
        {drafts.map((config, index) => (
          <section className="config-item" key={`${config.id}-${index}`}>
            <header className="config-item__header">
              <strong>{config.id || "未命名 API"}</strong>
              <div className="command-row">
                <button
                  className="secondary-command secondary-command--compact"
                  onClick={() => fetchModels(config)}
                  type="button"
                >
                  <Search size={16} />
                  <span>模型</span>
                </button>
                <button
                  className="danger-command"
                  onClick={() => removeConfig(index)}
                  type="button"
                >
                  <Trash2 size={16} />
                  <span>删除</span>
                </button>
              </div>
            </header>

            <div className="config-grid">
              <TextInput
                label="ID"
                onChange={(event) => updateDraft(index, "id", event.target.value)}
                value={config.id}
              />
              <TextInput
                label="URL"
                onChange={(event) => updateDraft(index, "url", event.target.value)}
                value={config.url}
              />
              <TextInput
                label="模型"
                onChange={(event) => updateDraft(index, "model", event.target.value)}
                value={config.model}
              />
              <label className="field-shell">
                <span className="field-label">Key</span>
                <span className="secret-input">
                  <input
                    className="text-control"
                    onChange={(event) => updateDraft(index, "key", event.target.value)}
                    type={visibleKeys[config.id] ? "text" : "password"}
                    value={config.key}
                  />
                  <button
                    aria-label="显示或隐藏 Key"
                    className="icon-button"
                    onClick={() =>
                      setVisibleKeys((current) => ({
                        ...current,
                        [config.id]: !current[config.id]
                      }))
                    }
                    title="显示或隐藏 Key"
                    type="button"
                  >
                    {visibleKeys[config.id] ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </span>
              </label>
              <TextInput
                label="Key 环境变量"
                onChange={(event) => updateDraft(index, "key_env_var", event.target.value)}
                value={config.key_env_var}
              />
              <NumberInput
                label="Max Tokens"
                min={0}
                onChange={(event) =>
                  updateDraft(index, "max_tokens", Number(event.target.value))
                }
                value={config.max_tokens}
              />
              <NumberInput
                label="Temperature"
                max={2}
                min={0}
                onChange={(event) =>
                  updateDraft(index, "temperature", Number(event.target.value))
                }
                step={0.1}
                value={config.temperature}
              />
              <NumberInput
                label="Timeout"
                min={1}
                onChange={(event) => updateDraft(index, "timeout", Number(event.target.value))}
                value={config.timeout}
              />
              <NumberInput
                label="Retries"
                min={1}
                onChange={(event) =>
                  updateDraft(index, "max_retries", Number(event.target.value))
                }
                value={config.max_retries}
              />
              <ToggleSwitch
                checked={config.stream}
                label="流式"
                onChange={(checked) => updateDraft(index, "stream", checked)}
              />
              <ToggleSwitch
                checked={config.is_active}
                label="启用"
                onChange={(checked) => updateDraft(index, "is_active", checked)}
              />
            </div>

            {modelOptions[config.id]?.length ? (
              <div className="model-list">
                {modelOptions[config.id].map((model) => (
                  <button
                    key={model}
                    onClick={() => updateDraft(index, "model", model)}
                    type="button"
                  >
                    {model}
                  </button>
                ))}
              </div>
            ) : null}
          </section>
        ))}
      </div>
    </section>
  );
}
