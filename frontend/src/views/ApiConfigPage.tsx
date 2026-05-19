import { Eye, EyeOff, Plus, RefreshCw, Save, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import { apiDisplayName } from "../api/display";
import type { ApiConfig } from "../api/types";
import { GuidancePanel } from "../components/common/Guidance";
import { NumberInput, TextInput, ToggleSwitch } from "../components/forms/FormControls";
import { useAppState } from "../state/AppState";

function nextPresetName(configs: ApiConfig[]) {
  const usedNames = new Set(configs.map((config) => apiDisplayName(config).toLocaleLowerCase()));
  let index = configs.length + 1;
  while (usedNames.has(`api ${index}`.toLocaleLowerCase())) {
    index += 1;
  }
  return `API ${index}`;
}

function createEmptyApiConfig(existingConfigs: ApiConfig[]): ApiConfig {
  return {
    id: `api_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    display_name: nextPresetName(existingConfigs),
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
  const nameIssues = useMemo(() => {
    const counts = new Map<string, number>();
    drafts.forEach((config) => {
      const name = apiDisplayName(config).trim().toLocaleLowerCase();
      if (name) {
        counts.set(name, (counts.get(name) ?? 0) + 1);
      }
    });
    return drafts.map((config) => {
      const name = config.display_name.trim();
      if (!name) {
        return "预设名称不能为空";
      }
      if ((counts.get(name.toLocaleLowerCase()) ?? 0) > 1) {
        return "预设名称不可重复";
      }
      return "";
    });
  }, [drafts]);
  const validationMessage = nameIssues.find(Boolean) ?? "";
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
    setDrafts((current) => [...current, createEmptyApiConfig(current)]);
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
    if (validationMessage) {
      dispatch({ type: "set_error", message: validationMessage });
      return;
    }
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
          <span>{validationMessage || statusText || `${drafts.length} 个配置`}</span>
        </div>
        <div className="command-row">
          <button className="secondary-command" onClick={reloadConfigs} title="重新读取本地 API 配置" type="button">
            <RefreshCw size={17} />
            <span>加载</span>
          </button>
          <button className="secondary-command" onClick={addConfig} title="新增一个 API 预设" type="button">
            <Plus size={17} />
            <span>新增</span>
          </button>
          <button
            className="primary-command"
            disabled={!isDirty || Boolean(validationMessage)}
            onClick={saveConfigs}
            title="保存当前 API 配置列表"
            type="button"
          >
            <Save size={17} />
            <span>保存</span>
          </button>
        </div>
      </div>

      <GuidancePanel
        title="API 配置说明"
        items={[
          "预设名称用于页面选择和日志显示；「全局启用」开启后该 API 才会出现在任务页面的候选列表中（第1层筛选）。",
          "Key 可直接填写，也可填写环境变量名；环境变量存在时会优先生效。",
          "模型按钮会用当前 URL 和 Key 拉取模型列表，点击返回的模型名可快速填入。"
        ]}
      />

      <div className="config-list">
        {drafts.map((config, index) => (
          <section className="config-item" key={`${config.id}-${index}`}>
            <header className="config-item__header">
              <strong>{apiDisplayName(config) || "未命名 API"}</strong>
              <div className="command-row">
                <button
                  className="secondary-command secondary-command--compact"
                  onClick={() => fetchModels(config)}
                  title="获取当前 API 可用模型"
                  type="button"
                >
                  <Search size={16} />
                  <span>模型</span>
                </button>
                <button
                  className="danger-command"
                  onClick={() => removeConfig(index)}
                  title="删除此 API 预设"
                  type="button"
                >
                  <Trash2 size={16} />
                  <span>删除</span>
                </button>
              </div>
            </header>

            <div className="config-grid">
              <TextInput
                label="预设名称"
                hint={nameIssues[index] || "用于页面选择和日志显示，不能重复"}
                onChange={(event) => updateDraft(index, "display_name", event.target.value)}
                value={config.display_name}
              />
              <TextInput
                label="URL"
                hint="填写兼容 OpenAI chat/completions 的 API 基础地址。"
                onChange={(event) => updateDraft(index, "url", event.target.value)}
                value={config.url}
              />
              <TextInput
                label="模型"
                hint="任务请求时使用的模型 ID。"
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
                <span className="field-hint">接口密钥会在加载配置时掩码显示。</span>
              </label>
              <TextInput
                label="Key 环境变量"
                hint="可填写项目根目录 .env 中的变量名"
                onChange={(event) => updateDraft(index, "key_env_var", event.target.value)}
                value={config.key_env_var}
              />
              <NumberInput
                label="Max Tokens"
                hint="限制模型单次最多生成 token 数；0 表示不主动传限制。"
                min={0}
                onChange={(event) =>
                  updateDraft(index, "max_tokens", Number(event.target.value))
                }
                value={config.max_tokens}
              />
              <NumberInput
                label="Temperature"
                hint="控制输出随机性，数值越高越发散。"
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
                hint="单次请求最长等待秒数。"
                min={1}
                onChange={(event) => updateDraft(index, "timeout", Number(event.target.value))}
                value={config.timeout}
              />
              <NumberInput
                label="Retries"
                hint="请求失败后的最大重试次数。"
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
                hint="关闭后该 API 不会出现在任何任务页面的可选列表中"
                label="全局启用"
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
