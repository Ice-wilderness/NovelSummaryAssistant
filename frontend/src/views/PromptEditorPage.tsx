import { RotateCcw, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import { SelectField, TextAreaField } from "../components/forms/FormControls";
import { useAppState } from "../state/AppState";

export function PromptEditorPage() {
  const { state, dispatch } = useAppState();
  const [selectedKey, setSelectedKey] = useState("");
  const selectedPrompt = useMemo(
    () => state.prompts.find((prompt) => prompt.key === selectedKey) ?? state.prompts[0],
    [selectedKey, state.prompts]
  );
  const [draft, setDraft] = useState("");
  const isDirty = Boolean(selectedPrompt && draft !== selectedPrompt.text);

  useEffect(() => {
    if (!selectedPrompt) {
      return;
    }
    setSelectedKey(selectedPrompt.key);
    setDraft(selectedPrompt.text);
  }, [selectedPrompt?.key]);

  const replacePrompt = (text: string) => {
    if (!selectedPrompt) {
      return;
    }
    dispatch({
      type: "set_prompts",
      items: state.prompts.map((prompt) =>
        prompt.key === selectedPrompt.key ? { ...prompt, text } : prompt
      )
    });
  };

  const savePrompt = async () => {
    if (!selectedPrompt) {
      return;
    }
    try {
      const saved = await apiClient.savePrompt(selectedPrompt.key, draft);
      replacePrompt(saved.text);
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      dispatch({
        type: "set_error",
        message: error instanceof Error ? error.message : String(error)
      });
    }
  };

  const resetPrompt = async () => {
    if (!selectedPrompt) {
      return;
    }
    try {
      const reset = await apiClient.resetPrompt(selectedPrompt.key);
      setDraft(reset.text);
      replacePrompt(reset.text);
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
          <span>{selectedPrompt?.filename ?? "未加载"}</span>
        </div>
        <div className="command-row">
          <button className="secondary-command" onClick={resetPrompt} type="button">
            <RotateCcw size={17} />
            <span>重置</span>
          </button>
          <button
            className="primary-command"
            disabled={!selectedPrompt || !isDirty}
            onClick={savePrompt}
            type="button"
          >
            <Save size={17} />
            <span>保存</span>
          </button>
        </div>
      </div>

      <div className="form-grid form-grid--two">
        <SelectField
          label="模板"
          onChange={(event) => setSelectedKey(event.target.value)}
          options={state.prompts.map((prompt) => ({
            label: prompt.key,
            value: prompt.key
          }))}
          value={selectedPrompt?.key ?? ""}
        />
        <div className="result-panel result-panel--compact">
          <strong>状态</strong>
          <span>{isDirty ? "未保存" : "已同步"}</span>
        </div>
      </div>

      <TextAreaField
        label="内容"
        onChange={(event) => setDraft(event.target.value)}
        value={draft}
      />
    </section>
  );
}
