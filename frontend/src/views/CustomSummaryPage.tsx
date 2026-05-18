import { Play } from "lucide-react";
import { useMemo, useState } from "react";
import { apiClient } from "../api/client";
import { SelectField, TextAreaField } from "../components/forms/FormControls";
import { useTaskActions } from "../hooks/useTaskActions";
import { useAppState } from "../state/AppState";

export function CustomSummaryPage() {
  const { state } = useAppState();
  const { startTask } = useTaskActions();
  const activeApis = useMemo(
    () => state.apiConfigs.filter((config) => config.is_active),
    [state.apiConfigs]
  );
  const latestCustomTask = state.taskOrder
    .map((taskId) => state.tasks[taskId])
    .find((task) => task.task_type === "custom_summary");
  const [filePathsText, setFilePathsText] = useState("");
  const [userPrompt, setUserPrompt] = useState("");
  const [apiId, setApiId] = useState("");
  const filePaths = filePathsText
    .split(/\r?\n/)
    .map((file) => file.trim())
    .filter(Boolean);
  const selectedApiId = apiId || activeApis[0]?.id || "";
  const canStart =
    filePaths.length > 0 && userPrompt.trim().length > 0 && selectedApiId.length > 0;

  const startCustomSummary = () => {
    void startTask(() =>
      apiClient.startCustomSummary({
        selected_file_paths: filePaths,
        user_prompt: userPrompt,
        api_id: selectedApiId
      })
    );
  };

  return (
    <section className="workflow-view">
      <div className="view-header">
        <div>
          <h2>自定义总结</h2>
          <span>{filePaths.length} 个文件</span>
        </div>
        <button
          className="primary-command"
          disabled={!canStart}
          onClick={startCustomSummary}
          type="button"
        >
          <Play size={18} />
          <span>开始</span>
        </button>
      </div>

      <div className="form-grid form-grid--two">
        <SelectField
          label="API"
          onChange={(event) => setApiId(event.target.value)}
          options={activeApis.map((config) => ({ label: config.id, value: config.id }))}
          value={selectedApiId}
        />
        <div className="result-panel result-panel--compact">
          <strong>结果</strong>
          <span>{latestCustomTask?.result_summary || latestCustomTask?.progress_text || "暂无结果"}</span>
        </div>
      </div>

      <TextAreaField
        label="文件路径"
        onChange={(event) => setFilePathsText(event.target.value)}
        value={filePathsText}
      />
      <TextAreaField
        label="自定义指令"
        onChange={(event) => setUserPrompt(event.target.value)}
        value={userPrompt}
      />
    </section>
  );
}
