import { Download, Edit3, FileInput, Plus, Save, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { apiClient } from "../../api/client";
import type { PatternConfig, PatternRegexMode } from "../../api/types";

interface Props {
  open: boolean;
  onClose: () => void;
  onConfigChanged?: () => void;
}

export function PatternConfigManager({ open, onClose, onConfigChanged }: Props) {
  const [configs, setConfigs] = useState<PatternConfig[]>([]);
  const [editing, setEditing] = useState<PatternConfig | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [name, setName] = useState("");
  const [pattern, setPattern] = useState("");
  const [regexMode, setRegexMode] = useState<PatternRegexMode>("raw");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      refreshConfigs();
    }
  }, [open]);

  const refreshConfigs = async () => {
    try {
      const items = await apiClient.listPatterns();
      setConfigs(items);
    } catch {
      setConfigs([]);
    }
  };

  const startNew = () => {
    setEditing(null);
    setIsNew(true);
    setName("");
    setPattern("");
    setRegexMode("raw");
    setDescription("");
    setError("");
  };

  const startEdit = (cfg: PatternConfig) => {
    setEditing(cfg);
    setIsNew(false);
    setName(cfg.name);
    setPattern(cfg.pattern);
    setRegexMode(cfg.regex_mode);
    setDescription(cfg.description);
    setError("");
  };

  const cancelEdit = () => {
    setEditing(null);
    setIsNew(false);
    setError("");
  };

  const saveConfig = async () => {
    setError("");
    if (!name.trim()) {
      setError("名称不能为空");
      return;
    }
    if (!pattern.trim()) {
      setError("正则表达式不能为空");
      return;
    }
    setLoading(true);
    try {
      if (isNew) {
        await apiClient.createPattern({
          name: name.trim(),
          pattern: pattern.trim(),
          regex_mode: regexMode,
          description: description.trim(),
        });
      } else if (editing) {
        await apiClient.updatePattern(editing.id, {
          name: name.trim(),
          pattern: pattern.trim(),
          regex_mode: regexMode,
          description: description.trim(),
        });
      }
      await refreshConfigs();
      cancelEdit();
      onConfigChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const deleteConfig = async (cfg: PatternConfig) => {
    if (cfg.is_preset) return;
    if (!window.confirm(`确定要删除配置「${cfg.name}」吗？`)) return;
    try {
      await apiClient.deletePattern(cfg.id);
      await refreshConfigs();
      onConfigChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const exportConfig = async (cfg: PatternConfig) => {
    try {
      const data = await apiClient.exportPattern(cfg.id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `chapter-pattern-${cfg.name.replace(/[^\w一-鿿]/g, "_")}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const importConfigs = async () => {
    fileInputRef.current?.click();
  };

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setLoading(true);
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      await apiClient.importPatterns(data);
      await refreshConfigs();
      onConfigChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败，请检查文件格式");
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel pattern-manager" onClick={(e) => e.stopPropagation()}>
        <header className="modal-header">
          <h3>正则配置管理</h3>
          <button className="icon-button" onClick={onClose} type="button" title="关闭">
            <X size={18} />
          </button>
        </header>

        <div className="pattern-manager__toolbar">
          <button className="secondary-command" onClick={startNew} type="button" disabled={loading}>
            <Plus size={16} />
            <span>新建</span>
          </button>
          <button className="secondary-command" onClick={importConfigs} type="button" disabled={loading}>
            <FileInput size={16} />
            <span>导入</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            style={{ display: "none" }}
            onChange={(event) => { void handleFileSelected(event); }}
          />
        </div>

        {error ? <span className="field-hint field-hint--warning">{error}</span> : null}

        {/* Edit form */}
        {(isNew || editing) ? (
          <div className="pattern-manager__edit">
            <input
              placeholder="配置名称"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <textarea
              placeholder={regexMode === "raw" ? "完整正则表达式" : "占位符模式（用 n 代表章节号）"}
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              rows={3}
            />
            <div className="pattern-manager__edit-row">
              <select
                value={regexMode}
                onChange={(e) => setRegexMode(e.target.value as PatternRegexMode)}
              >
                <option value="raw">raw — 完整正则</option>
                <option value="simple">simple — 占位符（n=章节号）</option>
              </select>
              <input
                placeholder="描述（可选）"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="pattern-manager__edit-actions">
              <button className="secondary-command" onClick={cancelEdit} type="button" disabled={loading}>
                取消
              </button>
              <button className="primary-command" onClick={() => { void saveConfig(); }} type="button" disabled={loading}>
                <Save size={16} />
                <span>保存</span>
              </button>
            </div>
          </div>
        ) : null}

        {/* Config list */}
        <div className="pattern-manager__list">
          {configs.length === 0 ? (
            <span className="empty-state">暂无配置，点击"新建"创建或"导入"已有配置</span>
          ) : null}
          {configs.map((cfg) => (
            <div className={`pattern-item ${cfg.is_preset ? "pattern-item--preset" : ""}`} key={cfg.id}>
              <div className="pattern-item__info">
                <div className="pattern-item__header">
                  <strong>{cfg.name}</strong>
                  <span className={`mode-badge mode-badge--${cfg.regex_mode}`}>
                    {cfg.regex_mode}
                  </span>
                  {cfg.is_preset ? <span className="preset-badge">预设</span> : null}
                </div>
                {cfg.description ? <span className="pattern-item__desc">{cfg.description}</span> : null}
                <code className="pattern-item__pattern">{cfg.pattern}</code>
              </div>
              <div className="pattern-item__actions">
                <button
                  className="icon-button"
                  onClick={() => startEdit(cfg)}
                  type="button"
                  title="编辑"
                >
                  <Edit3 size={16} />
                </button>
                <button
                  className="icon-button"
                  onClick={() => { void exportConfig(cfg); }}
                  type="button"
                  title="导出"
                >
                  <Download size={16} />
                </button>
                {!cfg.is_preset ? (
                  <button
                    className="icon-button icon-button--danger"
                    onClick={() => { void deleteConfig(cfg); }}
                    type="button"
                    title="删除"
                  >
                    <Trash2 size={16} />
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
