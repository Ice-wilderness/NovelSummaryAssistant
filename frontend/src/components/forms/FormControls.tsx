import { ExternalLink, FolderOpen, History, Plus, Save, Trash2, Upload, X } from "lucide-react";
import {
  useEffect,
  useState,
  type ChangeEvent,
  type DragEvent,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes
} from "react";
import type { ProjectProgress, ProjectRecord, UploadedFileRef } from "../../api/types";
import { IconButton } from "../common/IconButton";

function classNames(...values: Array<string | false | undefined>) {
  return values.filter(Boolean).join(" ");
}

function formatTime(value: number) {
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

interface FieldShellProps {
  label: string;
  hint?: string;
  children: ReactNode;
}

function FieldShell({ label, hint, children }: FieldShellProps) {
  return (
    <label className="field-shell">
      <span className="field-label">{label}</span>
      {children}
      {hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  );
}

type TextInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label: string;
  hint?: string;
};

export function TextInput({ label, hint, className, ...props }: TextInputProps) {
  return (
    <FieldShell label={label} hint={hint}>
      <input className={classNames("text-control", className)} type="text" {...props} />
    </FieldShell>
  );
}

type NumberInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label: string;
  hint?: string;
};

export function NumberInput({ label, hint, ...props }: NumberInputProps) {
  return (
    <FieldShell label={label} hint={hint}>
      <input className="text-control" type="number" {...props} />
    </FieldShell>
  );
}

interface ToggleSwitchProps {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function ToggleSwitch({ label, hint, checked, onChange, disabled }: ToggleSwitchProps) {
  return (
    <span className="toggle-shell">
      <label className="toggle-control">
        <input
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
          type="checkbox"
        />
        <span className="toggle-track" aria-hidden="true">
          <span className="toggle-thumb" />
        </span>
        <span className="field-label">{label}</span>
      </label>
      {hint ? <span className="field-hint">{hint}</span> : null}
    </span>
  );
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  hint?: string;
  options: Array<{ label: string; value: string }>;
}

export function SelectField({ label, hint, options, ...props }: SelectFieldProps) {
  return (
    <FieldShell label={label} hint={hint}>
      <select className="text-control" {...props}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
}

export function TextAreaField({
  label,
  hint,
  className,
  ...props
}: TextAreaFieldProps) {
  return (
    <FieldShell label={label} hint={hint}>
      <textarea
        className={classNames(
          "text-control",
          "text-control--area",
          className
        )}
        {...props}
      />
    </FieldShell>
  );
}

interface PathInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
  hint?: string;
  onBrowse?: () => void;
}

export function PathInput({
  label,
  hint,
  onBrowse,
  className,
  ...props
}: PathInputProps) {
  return (
    <FieldShell label={label} hint={hint}>
      <>
        <span className="path-input">
          <input className={classNames("text-control", className)} type="text" {...props} />
          <IconButton disabled={!onBrowse} label="选择路径" onClick={onBrowse}>
            <FolderOpen size={18} />
          </IconButton>
        </span>
      </>
    </FieldShell>
  );
}

interface FileListFieldProps {
  label: string;
  files: string[];
  onAdd?: () => void;
  onRemove?: (index: number) => void;
}

export function FileListField({ label, files, onAdd, onRemove }: FileListFieldProps) {
  return (
    <section className="file-list-field" aria-label={label}>
      <header className="file-list-header">
        <span className="field-label">{label}</span>
        <IconButton disabled={!onAdd} label="添加文件" onClick={onAdd}>
          <Plus size={18} />
        </IconButton>
      </header>
      <div className="file-list-body">
        {files.length === 0 ? (
          <span className="field-hint">暂无文件</span>
        ) : (
          files.map((file, index) => (
            <div className="file-row" key={`${file}-${index}`}>
              <span title={file}>{file}</span>
              <IconButton disabled={!onRemove} label="移除文件" onClick={() => onRemove?.(index)}>
                <X size={16} />
              </IconButton>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

interface UploadFileFieldProps {
  label: string;
  hint?: string;
  files: UploadedFileRef[];
  multiple?: boolean;
  isUploading?: boolean;
  onUpload: (files: FileList | File[]) => void;
  onRemove: (fileId: string) => void;
  onClear?: () => void;
}

export function UploadFileField({
  label,
  hint,
  files,
  multiple = true,
  isUploading = false,
  onUpload,
  onRemove,
  onClear
}: UploadFileFieldProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      onUpload(event.target.files);
      event.target.value = "";
    }
  };

  const handleDragOver = (event: DragEvent<HTMLElement>) => {
    if (isUploading) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (event: DragEvent<HTMLElement>) => {
    if (isUploading) {
      return;
    }
    event.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(event.dataTransfer.files);
    if (droppedFiles.length === 0) {
      return;
    }
    onUpload(multiple ? droppedFiles : droppedFiles.slice(0, 1));
  };

  return (
    <section
      className={classNames("file-list-field", "upload-field", isDragging && "upload-field--dragging")}
      aria-label={label}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <header className="file-list-header">
        <span className="file-list-title">
          <span className="field-label">{label}</span>
          <span className="field-hint">{files.length} 个文件</span>
        </span>
        <span className="file-list-actions">
          <button
            className="secondary-command secondary-command--compact"
            disabled={files.length === 0 || !onClear}
            onClick={onClear}
            type="button"
          >
            <X size={16} />
            <span>清空</span>
          </button>
          <label className="upload-command">
            <Upload size={16} />
            <span>{isUploading ? "上传中" : "选择文件"}</span>
            <input
              accept=".txt,text/plain"
              disabled={isUploading}
              multiple={multiple}
              onChange={handleChange}
              type="file"
            />
          </label>
        </span>
      </header>
      {hint ? <span className="field-hint">{hint}</span> : null}
      <div className="file-list-body file-list-body--scroll">
        {files.length === 0 ? (
          <span className="field-hint">暂无上传文件</span>
        ) : (
          files.map((file) => (
            <div className="file-row" key={file.id}>
              <span title={file.original_name}>
                {file.original_name}
                {file.missing ? "（缺失）" : ""}
              </span>
              <IconButton label="移除文件" onClick={() => onRemove(file.id)}>
                <X size={16} />
              </IconButton>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

interface ProjectHistoryFieldProps {
  projects: ProjectRecord[];
  value: string;
  onDelete: (projectSlug: string) => void;
  onNewProject: () => void;
  onRestore: (projectSlug: string) => void;
}

const busyProjectStatuses = new Set(["pending", "running", "paused", "canceling"]);

function statusText(status: string) {
  switch (status) {
    case "pending":
      return "等待";
    case "running":
      return "运行";
    case "paused":
      return "暂停";
    case "canceling":
      return "取消中";
    case "cancelled":
      return "已取消";
    case "success":
      return "完成";
    case "partial":
      return "部分";
    case "partial_failed":
      return "部分结果";
    case "failed":
      return "失败";
    case "interrupted":
      return "已中断";
    default:
      return status || "暂无";
  }
}

function workflowText(workflowType: string) {
  switch (workflowType) {
    case "novel_summary":
      return "小说总结";
    case "article_summary":
      return "文章总结";
    case "custom_summary":
      return "自定义总结";
    case "chapter_split":
      return "章节分割";
    default:
      return workflowType || "未知流程";
  }
}

function formatProjectTime(timestamp: number) {
  if (!timestamp) {
    return "无更新时间";
  }
  return new Date(timestamp * 1000).toLocaleString();
}

export function ProjectHistoryField({
  projects,
  value,
  onDelete,
  onNewProject,
  onRestore
}: ProjectHistoryFieldProps) {
  const handleDelete = (project: ProjectRecord) => {
    const status = String(project.latest_task_status || "");
    if (busyProjectStatuses.has(status)) {
      return;
    }
    const confirmed = window.confirm(
      `删除项目「${project.project_name}」？此操作会移除项目历史和确认归属的托管文件，无法确认归属的输出目录会保留。`
    );
    if (confirmed) {
      onDelete(project.project_slug);
    }
  };

  return (
    <FieldShell
      label="历史项目"
      hint="选择未完成或最近处理过的项目，可恢复项目名、上传文件和输出设置。"
    >
      <div className="history-panel">
        <div className="history-toolbar">
          <span className="history-toolbar__label">
            <History size={16} />
            <span>{projects.length} 个历史项目</span>
          </span>
          <button className="secondary-command secondary-command--compact" onClick={onNewProject} type="button">
            <Plus size={16} />
            <span>新项目</span>
          </button>
        </div>
        <div className="history-list">
          {projects.length === 0 ? (
            <span className="empty-state">暂无历史项目</span>
          ) : (
            projects.map((project) => {
              const status = String(project.latest_task_status || "");
              const deleteDisabled = busyProjectStatuses.has(status);
              return (
                <div
                  className={classNames(
                    "history-item",
                    value === project.project_slug && "history-item--active"
                  )}
                  key={project.project_slug}
                >
                  <button
                    className="history-item__restore"
                    onClick={() => onRestore(project.project_slug)}
                    type="button"
                  >
                    <span className={`status-pill status-pill--${status || "idle"}`}>
                      {statusText(status)}
                    </span>
                    <span className="history-item__content">
                      <strong title={project.project_name}>{project.project_name}</strong>
                      <small>
                        {workflowText(String(project.workflow_type))} · {formatProjectTime(project.updated_at)}
                      </small>
                    </span>
                  </button>
                  <IconButton
                    disabled={deleteDisabled}
                    label={deleteDisabled ? "任务未结束，不能删除" : "删除项目"}
                    onClick={() => handleDelete(project)}
                  >
                    <Trash2 size={16} />
                  </IconButton>
                </div>
              );
            })
          )}
        </div>
      </div>
    </FieldShell>
  );
}

interface ProjectActionRowProps {
  canSave: boolean;
  isSaving?: boolean;
  lastSavedAt?: number | null;
  onImport: () => void;
  onSave: () => void;
}

export function ProjectActionRow({
  canSave,
  isSaving = false,
  lastSavedAt = null,
  onImport,
  onSave
}: ProjectActionRowProps) {
  const [visibleSavedAt, setVisibleSavedAt] = useState<number | null>(null);

  useEffect(() => {
    if (!lastSavedAt) {
      setVisibleSavedAt(null);
      return;
    }
    setVisibleSavedAt(lastSavedAt);
    const timer = window.setTimeout(() => setVisibleSavedAt(null), 3200);
    return () => window.clearTimeout(timer);
  }, [lastSavedAt]);

  return (
    <div className="command-row">
      <button className="secondary-command secondary-command--compact" onClick={onImport} type="button">
        <FolderOpen size={16} />
        <span>导入项目</span>
      </button>
      <button
        className="secondary-command secondary-command--compact"
        disabled={!canSave || isSaving}
        onClick={onSave}
        type="button"
      >
        <Save size={16} />
        <span>{isSaving ? "保存中..." : "保存项目"}</span>
      </button>
      {visibleSavedAt ? (
        <div aria-live="polite" className="project-save-toast" role="status">
          <strong>项目已保存</strong>
          <span>{formatTime(visibleSavedAt)}</span>
        </div>
      ) : null}
    </div>
  );
}

interface ProjectProgressPanelProps {
  progress: ProjectProgress | null;
}

export function ProjectProgressPanel({ progress }: ProjectProgressPanelProps) {
  if (!progress) {
    return (
      <section className="project-progress-panel">
        <header>
          <strong>项目进度</strong>
          <span>暂无进度</span>
        </header>
      </section>
    );
  }
  const percent = Math.max(0, Math.min(100, Math.round(progress.percent || 0)));
  return (
    <section className="project-progress-panel">
      <header>
        <strong>项目进度</strong>
        <span>{progress.summary || "暂无进度"}</span>
      </header>
      <div className="project-progress-track" aria-label={`项目进度 ${percent}%`}>
        <span style={{ width: `${percent}%` }} />
      </div>
      <div className="project-progress-stages">
        {progress.stages.length === 0 ? (
          <span className="field-hint">暂无可显示的阶段进度</span>
        ) : (
          progress.stages.map((stage) => (
            <div className="project-progress-stage" key={stage.label}>
              <span>{stage.label}</span>
              <strong>
                {stage.total === null || stage.total === undefined
                  ? stage.completed
                  : `${stage.completed}/${stage.total}`}
              </strong>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

interface OutputDirectoryFieldProps {
  defaultDirectory: string;
  outputDirectory: string;
  onOutputDirectoryChange: (value: string) => void;
  onBrowseOutputDirectory: () => void;
  onOpenOutputDirectory: () => void;
  onUseDefaultDirectory: () => void;
  onValidateOutputDirectory: () => void;
}

export function OutputDirectoryField({
  defaultDirectory,
  outputDirectory,
  onOutputDirectoryChange,
  onBrowseOutputDirectory,
  onOpenOutputDirectory,
  onUseDefaultDirectory,
  onValidateOutputDirectory
}: OutputDirectoryFieldProps) {
  return (
    <section className="output-directory-field">
      <PathInput
        hint={
          defaultDirectory
            ? `默认：${defaultDirectory}`
            : "上传文件、导入项目或选择历史项目后会自动填充默认输出目录。"
        }
        label="输出目录"
        onBlur={onValidateOutputDirectory}
        onBrowse={onBrowseOutputDirectory}
        onChange={(event) => onOutputDirectoryChange(event.target.value)}
        value={outputDirectory}
      />
      <div className="command-row">
        <button className="secondary-command secondary-command--compact" onClick={onOpenOutputDirectory} type="button">
          <ExternalLink size={16} />
          <span>打开输出目录</span>
        </button>
        <button
          className="secondary-command secondary-command--compact"
          disabled={!defaultDirectory}
          onClick={onUseDefaultDirectory}
          type="button"
        >
          <X size={16} />
          <span>使用默认目录</span>
        </button>
      </div>
    </section>
  );
}
