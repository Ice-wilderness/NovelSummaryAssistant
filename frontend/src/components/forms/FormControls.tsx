import { ExternalLink, FolderOpen, History, Plus, Upload, X } from "lucide-react";
import {
  useState,
  type ChangeEvent,
  type DragEvent,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes
} from "react";
import { apiClient } from "../../api/client";
import type { ProjectRecord, UploadedFileRef } from "../../api/types";
import { IconButton } from "../common/IconButton";

type DroppedFile = File & {
  path?: string;
  webkitRelativePath?: string;
};

type PathKind = "directory" | "file" | "any";

const PATH_DROP_DEBUG_PREFIX = "[PathDropDebug]";

function classNames(...values: Array<string | false | undefined>) {
  return values.filter(Boolean).join(" ");
}

function normalizeDroppedValue(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  if (!trimmed.startsWith("file://")) {
    return trimmed;
  }
  try {
    const url = new URL(trimmed);
    const pathname = decodeURIComponent(url.pathname);
    if (pathname) {
      return pathname.replace(/^\/([A-Za-z]:)/, "$1");
    }
  } catch {
    // URL parse failed, strip file:// prefix manually
  }
  const stripped = trimmed.replace(/^file:\/\/\/?/i, "");
  return stripped || trimmed;
}

function splitDroppedText(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith("#"))
    .map(normalizeDroppedValue)
    .filter(Boolean);
}

function hasDirectorySegment(path: string) {
  const normalized = normalizeDroppedValue(path);
  return normalized.includes("/") || normalized.includes("\\");
}

function describeDroppedFile(file: File) {
  const droppedFile = file as DroppedFile;
  return {
    name: droppedFile.name,
    path: droppedFile.path,
    webkitRelativePath: droppedFile.webkitRelativePath,
    type: droppedFile.type,
    size: droppedFile.size,
    lastModified: droppedFile.lastModified,
    keys: Object.keys(droppedFile)
  };
}

function describeDataTransferItems(event: DragEvent<HTMLElement>) {
  return Array.from(event.dataTransfer.items ?? []).map((item, index) => {
    const file = item.kind === "file" ? item.getAsFile() : null;
    return {
      index,
      kind: item.kind,
      type: item.type,
      file: file ? describeDroppedFile(file) : null
    };
  });
}

function getDroppedPaths(event: DragEvent<HTMLElement>) {
  const uriList = event.dataTransfer.getData("text/uri-list");
  const plainText = event.dataTransfer.getData("text/plain");
  const files = Array.from(event.dataTransfer.files);
  const paths = [
    ...splitDroppedText(uriList),
    ...splitDroppedText(plainText),
    ...files
      .map((file) => {
        const droppedFile = file as DroppedFile;
        return droppedFile.path || droppedFile.webkitRelativePath || droppedFile.name;
      })
      .filter((path): path is string => Boolean(path))
  ];
  console.info(`${PATH_DROP_DEBUG_PREFIX} raw drop data`, {
    types: Array.from(event.dataTransfer.types ?? []),
    uriList,
    plainText,
    files: files.map(describeDroppedFile),
    items: describeDataTransferItems(event),
    candidatesBeforeSort: [...paths]
  });
  paths.sort((a, b) => Number(hasDirectorySegment(b)) - Number(hasDirectorySegment(a)));
  const uniquePaths = [...new Set(paths)];
  console.info(`${PATH_DROP_DEBUG_PREFIX} selected candidates`, {
    candidatesAfterSort: paths,
    uniquePaths
  });
  return uniquePaths;
}

function parentPathFromString(path: string) {
  const cleanPath = normalizeDroppedValue(path);
  const lastSep = Math.max(cleanPath.lastIndexOf("/"), cleanPath.lastIndexOf("\\"));
  if (lastSep <= 0) {
    return "";
  }
  return cleanPath.slice(0, lastSep);
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

export function TextInput({ label, hint, ...props }: TextInputProps) {
  return (
    <FieldShell label={label} hint={hint}>
      <input className="text-control" type="text" {...props} />
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
  onDropPaths?: (paths: string[]) => void;
}

export function TextAreaField({
  label,
  hint,
  onDropPaths,
  className,
  onDragLeave,
  onDragOver,
  onDrop,
  ...props
}: TextAreaFieldProps) {
  const [isDragging, setIsDragging] = useState(false);
  const canDropPaths = Boolean(onDropPaths);

  const handleDragOver = (event: DragEvent<HTMLTextAreaElement>) => {
    onDragOver?.(event);
    if (!canDropPaths) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setIsDragging(true);
  };

  const handleDragLeave = (event: DragEvent<HTMLTextAreaElement>) => {
    onDragLeave?.(event);
    setIsDragging(false);
  };

  const handleDrop = async (event: DragEvent<HTMLTextAreaElement>) => {
    onDrop?.(event);
    if (!canDropPaths) {
      return;
    }
    event.preventDefault();
    setIsDragging(false);
    const paths = getDroppedPaths(event);
    if (paths.length === 0) {
      console.info(`${PATH_DROP_DEBUG_PREFIX} textarea drop ignored: no paths`);
      return;
    }
    try {
      const resolved = await Promise.all(
        paths.map((p) =>
          apiClient.resolvePath(p).then((r) => r.path || p)
        )
      );
      console.info(`${PATH_DROP_DEBUG_PREFIX} textarea resolved paths`, { paths, resolved });
      onDropPaths?.(resolved);
    } catch (error) {
      console.warn(`${PATH_DROP_DEBUG_PREFIX} textarea resolve failed`, { paths, error });
      onDropPaths?.(paths);
    }
  };

  return (
    <FieldShell label={label} hint={hint}>
      <textarea
        className={classNames(
          "text-control",
          "text-control--area",
          canDropPaths && "drop-target",
          isDragging && "drop-target--active",
          className
        )}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        {...props}
      />
    </FieldShell>
  );
}

interface PathInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
  hint?: string;
  onBrowse?: () => void;
  onDropPath?: (path: string) => void;
  pathKind?: PathKind;
}

export function PathInput({
  label,
  hint,
  onBrowse,
  onDropPath,
  pathKind = "any",
  className,
  ...props
}: PathInputProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [dropMessage, setDropMessage] = useState("");
  const canDropPath = Boolean(onDropPath);

  const handleDragOver = (event: DragEvent<HTMLSpanElement>) => {
    if (!canDropPath) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setIsDragging(true);
    setDropMessage("");
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (event: DragEvent<HTMLSpanElement>) => {
    if (!canDropPath) {
      return;
    }
    event.preventDefault();
    setIsDragging(false);
    const [droppedPath] = getDroppedPaths(event);
    if (!droppedPath) {
      console.info(`${PATH_DROP_DEBUG_PREFIX} path input drop ignored: no selected path`, {
        label,
        pathKind
      });
      return;
    }

    let resolvedPath = "";
    try {
      const resolved = await apiClient.resolvePath(droppedPath, pathKind === "directory");
      resolvedPath = resolved.path;
      console.info(`${PATH_DROP_DEBUG_PREFIX} path input resolved`, {
        label,
        pathKind,
        droppedPath,
        resolved
      });
      if (resolved.resolved && resolved.path) {
        onDropPath?.(resolved.path);
        setDropMessage("");
        return;
      }
    } catch (error) {
      console.warn(`${PATH_DROP_DEBUG_PREFIX} path input resolve failed`, {
        label,
        pathKind,
        droppedPath,
        error
      });
    }

    if (pathKind === "directory") {
      const parentPath = parentPathFromString(droppedPath);
      if (parentPath) {
        console.info(`${PATH_DROP_DEBUG_PREFIX} path input fallback parent`, {
          label,
          droppedPath,
          parentPath
        });
        onDropPath?.(parentPath);
        setDropMessage("");
        return;
      }
      const resolvedParentPath = parentPathFromString(resolvedPath);
      if (resolvedParentPath && resolvedPath !== droppedPath) {
        console.info(`${PATH_DROP_DEBUG_PREFIX} path input fallback resolved parent`, {
          label,
          droppedPath,
          resolvedPath,
          resolvedParentPath
        });
        onDropPath?.(resolvedParentPath);
        setDropMessage("");
        return;
      }
      console.warn(`${PATH_DROP_DEBUG_PREFIX} path input cannot infer directory`, {
        label,
        droppedPath,
        resolvedPath
      });
      setDropMessage("浏览器未提供完整文件路径，请使用浏览按钮或粘贴完整路径。");
      return;
    }

    const finalPath = resolvedPath || normalizeDroppedValue(droppedPath);
    console.info(`${PATH_DROP_DEBUG_PREFIX} path input final path`, {
      label,
      pathKind,
      droppedPath,
      resolvedPath,
      finalPath
    });
    onDropPath?.(finalPath);
    setDropMessage("");
  };

  return (
    <FieldShell label={label} hint={hint}>
      <>
        <span
          className={classNames(
            "path-input",
            canDropPath && "path-input--drop-target",
            isDragging && "path-input--drop-active"
          )}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <input className={classNames("text-control", className)} type="text" {...props} />
          <IconButton disabled={!onBrowse} label="选择路径" onClick={onBrowse}>
            <FolderOpen size={18} />
          </IconButton>
        </span>
        {dropMessage ? <span className="field-hint">{dropMessage}</span> : null}
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
  onUpload: (files: FileList) => void;
  onRemove: (fileId: string) => void;
}

export function UploadFileField({
  label,
  hint,
  files,
  multiple = true,
  isUploading = false,
  onUpload,
  onRemove
}: UploadFileFieldProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      onUpload(event.target.files);
      event.target.value = "";
    }
  };

  return (
    <section className="file-list-field upload-field" aria-label={label}>
      <header className="file-list-header">
        <span className="field-label">{label}</span>
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
      </header>
      {hint ? <span className="field-hint">{hint}</span> : null}
      <div className="file-list-body">
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
  onRestore: (projectSlug: string) => void;
}

export function ProjectHistoryField({ projects, value, onRestore }: ProjectHistoryFieldProps) {
  return (
    <FieldShell
      label="历史项目"
      hint="选择未完成或最近处理过的项目，可恢复项目名、上传文件和输出设置。"
    >
      <span className="history-select">
        <History size={16} />
        <select
          className="text-control"
          onChange={(event) => onRestore(event.target.value)}
          value={value}
        >
          <option value="">新项目</option>
          {projects.map((project) => (
            <option key={project.project_slug} value={project.project_slug}>
              {project.project_name}
              {project.latest_task_status ? ` · ${project.latest_task_status}` : ""}
            </option>
          ))}
        </select>
      </span>
    </FieldShell>
  );
}

interface OutputDirectoryFieldProps {
  defaultDirectory: string;
  customDirectory: string;
  onCustomDirectoryChange: (value: string) => void;
  onBrowseCustomDirectory: () => void;
  onOpenDefaultDirectory: () => void;
  onOpenCustomDirectory: () => void;
}

export function OutputDirectoryField({
  defaultDirectory,
  customDirectory,
  onCustomDirectoryChange,
  onBrowseCustomDirectory,
  onOpenDefaultDirectory,
  onOpenCustomDirectory
}: OutputDirectoryFieldProps) {
  return (
    <section className="output-directory-field">
      <div className="field-shell">
        <span className="field-label">默认导出目录</span>
        <span className="path-input">
          <input
            className="text-control"
            readOnly
            value={defaultDirectory || "上传文件后生成项目默认导出目录"}
          />
          <IconButton label="打开默认导出目录" onClick={onOpenDefaultDirectory}>
            <ExternalLink size={18} />
          </IconButton>
        </span>
        <span className="field-hint">未选择自定义目录时，生成文件会写入项目默认导出目录。</span>
      </div>
      <PathInput
        hint="可选；选择后本次任务使用该目录，清空后回到默认导出目录。"
        label="自定义输出目录"
        onBrowse={onBrowseCustomDirectory}
        onChange={(event) => onCustomDirectoryChange(event.target.value)}
        value={customDirectory}
      />
      <div className="command-row">
        <button className="secondary-command secondary-command--compact" onClick={onOpenCustomDirectory} type="button">
          <ExternalLink size={16} />
          <span>打开自定义目录</span>
        </button>
        <button
          className="secondary-command secondary-command--compact"
          onClick={() => onCustomDirectoryChange("")}
          type="button"
        >
          <X size={16} />
          <span>使用默认目录</span>
        </button>
      </div>
    </section>
  );
}
