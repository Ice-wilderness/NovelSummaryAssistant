import { Play } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import { defaultNovelWordCounts } from "../api/defaults";
import type { NovelWordCounts } from "../api/types";
import { NumberInput, PathInput, SelectField, TextInput, ToggleSwitch } from "../components/forms/FormControls";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useTaskActions } from "../hooks/useTaskActions";
import { useAppState } from "../state/AppState";

const novelWordCountFields: Array<{ key: keyof NovelWordCounts; label: string }> = [
  { key: "small_summary_word_count", label: "小结总结" },
  { key: "small_plot_word_count", label: "小结剧情" },
  { key: "small_char_word_count", label: "小结角色" },
  { key: "big_plot_word_count", label: "大结剧情" },
  { key: "big_char_word_count", label: "大结角色" },
  { key: "super_plot_p1_word_count", label: "超级剧情 P1" },
  { key: "super_plot_p2_word_count", label: "超级剧情 P2" },
  { key: "super_char_p1_word_count", label: "超级角色 P1" },
  { key: "super_char_p2_word_count", label: "超级角色 P2" },
  { key: "ultimate_plot_p1_word_count", label: "终极剧情 P1" },
  { key: "ultimate_plot_p2_word_count", label: "终极剧情 P2" },
  { key: "ultimate_char_p1_word_count", label: "终极角色 P1" },
  { key: "ultimate_char_p2_word_count", label: "终极角色 P2" }
];

export function NovelSummaryPage() {
  const { state } = useAppState();
  const { startTask } = useTaskActions();
  const { isTaskBusy } = useTaskAvailability();
  const activeApis = useMemo(
    () => state.apiConfigs.filter((config) => config.is_active),
    [state.apiConfigs]
  );
  const [sourceFolderPath, setSourceFolderPath] = useState("");
  const [activeApiIds, setActiveApiIds] = useState<string[]>([]);
  const [bigSummaryBatchSize, setBigSummaryBatchSize] = useState(5);
  const [superSummaryThreshold, setSuperSummaryThreshold] = useState(5);
  const [ultimateApiId, setUltimateApiId] = useState("");
  const [useFineGrainedFlow, setUseFineGrainedFlow] = useState(false);
  const [wordCounts, setWordCounts] = useState<NovelWordCounts>(defaultNovelWordCounts);

  useEffect(() => {
    if (activeApiIds.length === 0 && activeApis.length > 0) {
      setActiveApiIds(activeApis.map((config) => config.id));
      setUltimateApiId(activeApis[0].id);
    }
  }, [activeApiIds.length, activeApis]);

  const updateWordCount = (key: keyof NovelWordCounts, value: string) => {
    setWordCounts((current) => ({ ...current, [key]: value }));
  };

  const toggleApi = (apiId: string, checked: boolean) => {
    setActiveApiIds((current) =>
      checked ? [...new Set([...current, apiId])] : current.filter((id) => id !== apiId)
    );
  };

  const startNovelSummary = () => {
    void startTask(() =>
      apiClient.startNovelSummary({
        source_folder_path: sourceFolderPath,
        active_api_ids: activeApiIds,
        big_summary_batch_size: bigSummaryBatchSize,
        super_summary_threshold: superSummaryThreshold,
        ultimate_api_id: ultimateApiId,
        use_fine_grained_flow: useFineGrainedFlow,
        word_counts: wordCounts
      })
    );
  };
  const canStart =
    sourceFolderPath.trim().length > 0 &&
    activeApiIds.length > 0 &&
    bigSummaryBatchSize > 0 &&
    superSummaryThreshold > 0 &&
    !isTaskBusy;

  return (
    <section className="workflow-view">
      <div className="view-header">
        <div>
          <h2>小说总结</h2>
          <span>{activeApis.length} 个启用 API</span>
        </div>
        <button
          className="primary-command"
          disabled={!canStart}
          onClick={startNovelSummary}
          type="button"
        >
          <Play size={18} />
          <span>开始</span>
        </button>
      </div>

      <div className="form-grid form-grid--two">
        <PathInput
          label="小说目录"
          onChange={(event) => setSourceFolderPath(event.target.value)}
          value={sourceFolderPath}
        />
        <SelectField
          label="终极总结 API"
          onChange={(event) => setUltimateApiId(event.target.value)}
          options={activeApis.map((config) => ({ label: config.id, value: config.id }))}
          value={ultimateApiId}
        />
        <NumberInput
          label="大总结批量"
          min={1}
          onChange={(event) => setBigSummaryBatchSize(Number(event.target.value))}
          value={bigSummaryBatchSize}
        />
        <NumberInput
          label="超级总结阈值"
          min={1}
          onChange={(event) => setSuperSummaryThreshold(Number(event.target.value))}
          value={superSummaryThreshold}
        />
      </div>

      <section className="option-band">
        <ToggleSwitch
          checked={useFineGrainedFlow}
          label="精细流程"
          onChange={setUseFineGrainedFlow}
        />
        <div className="checkbox-list" aria-label="启用 API">
          {activeApis.length === 0 ? (
            <span className="field-hint">暂无启用 API</span>
          ) : (
            activeApis.map((config) => (
              <label className="check-row" key={config.id}>
                <input
                  checked={activeApiIds.includes(config.id)}
                  onChange={(event) => toggleApi(config.id, event.target.checked)}
                  type="checkbox"
                />
                <span>{config.id}</span>
              </label>
            ))
          )}
        </div>
      </section>

      <section className="word-count-section">
        <h3>字数设置</h3>
        <div className="word-count-grid">
          {novelWordCountFields.map((field) => (
            <TextInput
              key={field.key}
              label={field.label}
              onChange={(event) => updateWordCount(field.key, event.target.value)}
              value={wordCounts[field.key]}
            />
          ))}
        </div>
      </section>
    </section>
  );
}
