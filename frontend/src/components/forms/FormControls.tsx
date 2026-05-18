import { FolderOpen, Plus, X } from "lucide-react";
import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes
} from "react";
import { IconButton } from "../common/IconButton";

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
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function ToggleSwitch({ label, checked, onChange, disabled }: ToggleSwitchProps) {
  return (
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

export function TextAreaField({ label, hint, ...props }: TextAreaFieldProps) {
  return (
    <FieldShell label={label} hint={hint}>
      <textarea className="text-control text-control--area" {...props} />
    </FieldShell>
  );
}

interface PathInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
  hint?: string;
  onBrowse?: () => void;
}

export function PathInput({ label, hint, onBrowse, ...props }: PathInputProps) {
  return (
    <FieldShell label={label} hint={hint}>
      <span className="path-input">
        <input className="text-control" type="text" {...props} />
        <IconButton disabled={!onBrowse} label="选择路径" onClick={onBrowse}>
          <FolderOpen size={18} />
        </IconButton>
      </span>
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
