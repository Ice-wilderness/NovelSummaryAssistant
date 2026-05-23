import { Settings } from "lucide-react";
import { useEffect, useState } from "react";
import { apiClient } from "../../api/client";
import type { PatternConfig } from "../../api/types";
import { PatternConfigManager } from "./PatternConfigManager";

interface Props {
  configId: string;
  onChange: (configId: string) => void;
}

export function PatternSelector({ configId, onChange }: Props) {
  const [configs, setConfigs] = useState<PatternConfig[]>([]);
  const [managerOpen, setManagerOpen] = useState(false);

  useEffect(() => {
    refreshConfigs();
  }, []);

  const refreshConfigs = async () => {
    try {
      const items = await apiClient.listPatterns();
      setConfigs(items);
    } catch {
      setConfigs([]);
    }
  };

  const selected = configs.find((c) => c.id === configId);
  const handleManagerClose = () => {
    setManagerOpen(false);
    refreshConfigs();
  };

  return (
    <div className="pattern-selector">
      <div className="pattern-selector__row">
        <select
          value={configId}
          onChange={(e) => onChange(e.target.value)}
        >
          {configs.length === 0 ? (
            <option value="">暂无配置</option>
          ) : null}
          {configs.map((cfg) => (
            <option key={cfg.id} value={cfg.id}>
              {cfg.name} ({cfg.regex_mode})
            </option>
          ))}
        </select>
        <button
          className="icon-button"
          onClick={() => setManagerOpen(true)}
          type="button"
          title="管理正则配置"
        >
          <Settings size={16} />
        </button>
      </div>
      {selected ? (
        <code className="pattern-selector__preview">{selected.pattern}</code>
      ) : (
        <span className="field-hint">请选择正则配置或点击齿轮图标新建</span>
      )}
      <PatternConfigManager
        open={managerOpen}
        onClose={handleManagerClose}
        onConfigChanged={refreshConfigs}
      />
    </div>
  );
}
