import { Play } from "lucide-react";
import { useMemo, useState } from "react";
import { apiClient } from "../api/client";
import { apiDisplayName } from "../api/display";
import { GuidancePanel } from "../components/common/Guidance";
import { SelectField, TextAreaField } from "../components/forms/FormControls";
import { appendImportedPaths } from "../hooks/usePathPicker";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useTaskActions } from "../hooks/useTaskActions";
import { useAppState } from "../state/AppState";

export function CustomSummaryPage() {
  const { state } = useAppState();
  const { startTask } = useTaskActions();
  const { isTaskBusy } = useTaskAvailability();
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
    filePaths.length > 0 &&
    userPrompt.trim().length > 0 &&
    selectedApiId.length > 0 &&
    !isTaskBusy;

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
          title="启动自定义总结任务"
          type="button"
        >
          <Play size={18} />
          <span>开始</span>
        </button>
      </div>

      <GuidancePanel
        title="自定义总结流程"
        items={[
          "文件路径每行一个，任务会读取这些文件并按你填写的自定义指令生成结果。",
          "API 决定本次任务使用哪个模型配置；未手动选择时默认使用第一个启用 API。",
          "自定义指令是本工作流的核心提示词，不会覆盖提示词页面中的持久化节点。"
        ]}
      />

      <div className="form-grid form-grid--two">
        <SelectField
          hint="用于执行本次自定义总结的 API 配置。"
          label="API"
          onChange={(event) => setApiId(event.target.value)}
          options={activeApis.map((config) => ({
            label: apiDisplayName(config),
            value: config.id
          }))}
          value={selectedApiId}
        />
        <div className="result-panel result-panel--compact">
          <strong>结果</strong>
          <span>{latestCustomTask?.result_summary || latestCustomTask?.progress_text || "暂无结果"}</span>
        </div>
      </div>

      <TextAreaField
        hint="每行一个文件路径；支持拖入文件追加。"
        label="文件路径"
        onChange={(event) => setFilePathsText(event.target.value)}
        onDropPaths={(paths) =>
          setFilePathsText((current) => appendImportedPaths(current, paths))
        }
        value={filePathsText}
      />
      <TextAreaField
        hint="描述你希望模型如何阅读、提取和输出这些文件内容。"
        label="自定义指令"
        onChange={(event) => setUserPrompt(event.target.value)}
        value={userPrompt}
      />
    </section>
  );
}
