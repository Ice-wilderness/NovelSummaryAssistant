import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import { assertFilesWithinUploadLimit } from "../api/uploadLimits";
import type {
  DeleteProjectResponse,
  ProjectProgress,
  ProjectRecord,
  SummaryOutputFormat,
  UploadedFileRef,
  WorkflowType
} from "../api/types";
import { useAppState } from "../state/AppState";

function pad(value: number) {
  return String(value).padStart(2, "0");
}

function timestampProjectName() {
  const now = new Date();
  return [
    "project",
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    "-",
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds())
  ].join("");
}

function fileStem(name: string) {
  const cleanName = name.trim();
  const dotIndex = cleanName.lastIndexOf(".");
  return dotIndex > 0 ? cleanName.slice(0, dotIndex) : cleanName;
}

function deriveProjectName(files: File[]) {
  if (files.length === 1) {
    return fileStem(files[0].name) || timestampProjectName();
  }
  return timestampProjectName();
}

const terminalStatuses = new Set(["cancelled", "partial_failed", "success", "failed", "interrupted"]);
const PROJECT_PROGRESS_REFRESH_MS = 5000;

interface SaveProjectOptions {
  summary_output_format?: SummaryOutputFormat;
  summary_batch_size?: number;
  use_fine_grained_flow?: boolean;
}

function formatDeleteProjectMessage(response: DeleteProjectResponse) {
  const preserved = response.preserved_output_directories || [];
  if (preserved.length === 0) {
    return "项目已删除";
  }
  const first = preserved[0];
  const suffix = preserved.length > 1 ? ` 等 ${preserved.length} 个目录` : "";
  return `项目已删除，已保留输出目录：${first.path}${suffix}。${first.message}`;
}

function uniqueMessages(messages: string[]) {
  return messages.filter((message, index) => message && messages.indexOf(message) === index);
}

export function useManagedProject(workflowType: WorkflowType) {
  const { state } = useAppState();
  const [projectName, setProjectName] = useState("");
  const [projectSlug, setProjectSlug] = useState("");
  const [defaultOutputDirectory, setDefaultOutputDirectory] = useState("");
  const [outputDirectory, setOutputDirectoryState] = useState("");
  const [outputDirectoryError, setOutputDirectoryError] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRef[]>([]);
  const [progress, setProgress] = useState<ProjectProgress | null>(null);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [savedProject, setSavedProject] = useState<ProjectRecord | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const uploadedFileIds = useMemo(
    () => uploadedFiles.filter((file) => !file.missing).map((file) => file.id),
    [uploadedFiles]
  );
  const customOutputDirectory = useMemo(() => {
    const output = outputDirectory.trim();
    const defaultOutput = defaultOutputDirectory.trim();
    if (!output || output === defaultOutput) {
      return "";
    }
    return output;
  }, [defaultOutputDirectory, outputDirectory]);
  const warnings = useMemo(
    () =>
      uniqueMessages([
        ...uploadedFiles.filter((file) => file.missing).map((file) => `${file.original_name} 已缺失`),
        ...(savedProject?.warnings || [])
      ]),
    [savedProject, uploadedFiles]
  );
  const isProjectDirty = useMemo(() => {
    if (!projectSlug || !savedProject) {
      return false;
    }
    const currentUploadIds = uploadedFileIds.join("|");
    const savedUploadIds = savedProject.uploads
      .filter((file) => !file.missing)
      .map((file) => file.id)
      .join("|");
    return (
      projectName.trim() !== savedProject.project_name ||
      customOutputDirectory !== savedProject.custom_output_directory ||
      currentUploadIds !== savedUploadIds
    );
  }, [customOutputDirectory, projectName, projectSlug, savedProject, uploadedFileIds]);
  const canSaveProject = Boolean(projectSlug) && !isUploading && !isSaving;
  const terminalProjectRefreshKey = useMemo(() => {
    const task = state.taskOrder
      .map((taskId) => state.tasks[taskId])
      .find((item) => {
        if (!item || !terminalStatuses.has(item.status)) {
          return false;
        }
        const params = item.params_summary as Record<string, unknown>;
        const taskProjectSlug = String(params.project_slug || "");
        if (!taskProjectSlug) {
          return false;
        }
        if (item.task_type === "project_repair") {
          return !projectSlug || taskProjectSlug === projectSlug;
        }
        const taskWorkflow =
          item.task_type === "small_summary_preparation" ? "novel_summary" : item.task_type;
        return taskWorkflow === workflowType;
      });
    return task ? `${task.task_id}:${task.status}:${task.updated_at}` : "";
  }, [projectSlug, state.taskOrder, state.tasks, workflowType]);
  const activeProjectTaskId = useMemo(() => {
    if (!projectSlug) {
      return "";
    }
    const task = state.taskOrder
      .map((taskId) => state.tasks[taskId])
      .find((item) => {
        if (!item || terminalStatuses.has(item.status)) {
          return false;
        }
        const taskWorkflow =
          item.task_type === "small_summary_preparation" ? "novel_summary" : item.task_type;
        if (item.task_type !== "project_repair" && taskWorkflow !== workflowType) {
          return false;
        }
        const params = item.params_summary as Record<string, unknown>;
        return String(params.project_slug || "") === projectSlug;
      });
    return task?.task_id || "";
  }, [projectSlug, state.taskOrder, state.tasks, workflowType]);

  const setOutputDirectory = useCallback((value: string) => {
    setOutputDirectoryState(value);
    setOutputDirectoryError("");
  }, []);

  const refreshProjects = useCallback(async () => {
    try {
      setProjects(await apiClient.listProjects(workflowType));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "加载历史项目失败");
    }
  }, [workflowType]);

  useEffect(() => {
    void refreshProjects();
  }, [refreshProjects]);

  const applyProject = useCallback((project: ProjectRecord) => {
    setProjectName(project.project_name);
    setProjectSlug(project.project_slug);
    setDefaultOutputDirectory(project.default_output_directory);
    setOutputDirectoryState(project.custom_output_directory || project.default_output_directory);
    setOutputDirectoryError("");
    setUploadedFiles(project.uploads);
    setProgress(project.progress);
    setSavedProject(project);
    setLastSavedAt(null);
    setMessage(project.latest_task_status ? `最近任务：${project.latest_task_status}` : "");
    setError("");
  }, []);

  const resetProjectState = useCallback(() => {
    setProjectName("");
    setProjectSlug("");
    setDefaultOutputDirectory("");
    setOutputDirectoryState("");
    setOutputDirectoryError("");
    setUploadedFiles([]);
    setProgress(null);
    setSavedProject(null);
    setLastSavedAt(null);
    setMessage("");
    setError("");
  }, []);

  const startNewProject = useCallback(() => {
    resetProjectState();
  }, [resetProjectState]);

  const restoreProject = useCallback(
    async (slug: string) => {
      if (!slug) {
        return;
      }
      try {
        const project = await apiClient.getProject(slug);
        applyProject(project);
      } catch (restoreError) {
        setError(restoreError instanceof Error ? restoreError.message : "恢复历史项目失败");
      }
    },
    [applyProject]
  );

  const refreshProjectState = useCallback(async () => {
    await refreshProjects();
    if (!projectSlug) {
      return;
    }
    try {
      const project = await apiClient.getProject(projectSlug);
      applyProject(project);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "刷新项目状态失败");
    }
  }, [applyProject, projectSlug, refreshProjects]);

  useEffect(() => {
    if (terminalProjectRefreshKey) {
      void refreshProjectState();
    }
  }, [refreshProjectState, terminalProjectRefreshKey]);

  useEffect(() => {
    if (!activeProjectTaskId) {
      return;
    }
    void refreshProjectState();
    const timer = window.setInterval(() => {
      void refreshProjectState();
    }, PROJECT_PROGRESS_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [activeProjectTaskId, refreshProjectState]);

  const uploadFiles = useCallback(
    async (fileList: FileList | File[]) => {
      const files = Array.from(fileList);
      if (files.length === 0) {
        return;
      }
      const effectiveProjectName = projectName.trim() || deriveProjectName(files);
      setProjectName(effectiveProjectName);
      setIsUploading(true);
      setError("");
      setMessage("");
      try {
        assertFilesWithinUploadLimit(files);
        const uploadFiles = await Promise.all(
          files.map(async (file) => {
            const buf = await file.arrayBuffer();
            // UTF-8 优先，失败或乱码时回退到 GBK
            const utf8 = new TextDecoder("utf-8", { fatal: false }).decode(buf);
            if (!utf8.includes("�") && !utf8.includes(" ")) {
              return { name: file.name, content: utf8 };
            }
            try {
              const gbk = new TextDecoder("gbk", { fatal: true }).decode(buf);
              return { name: file.name, content: gbk };
            } catch {
              return { name: file.name, content: utf8 };
            }
          })
        );
        const response = await apiClient.uploadTextFiles(
          effectiveProjectName,
          workflowType,
          uploadFiles,
          projectSlug
        );
        applyProject(response.project);
        if (!response.project.custom_output_directory) {
          setOutputDirectoryState(response.workflow_output_directory);
        }
        setMessage(`已上传 ${response.items.length} 个文件`);
        void refreshProjects();
      } catch (uploadError) {
        setError(uploadError instanceof Error ? uploadError.message : "上传失败");
      } finally {
        setIsUploading(false);
      }
    },
    [applyProject, projectName, projectSlug, refreshProjects, workflowType]
  );

  const removeUploadedFile = useCallback((fileId: string) => {
    setUploadedFiles((current) => current.filter((file) => file.id !== fileId));
    setMessage("已从项目草稿移除文件，保存项目后生效。");
  }, []);

  const clearUploadedFiles = useCallback(() => {
    setUploadedFiles([]);
    setMessage("已清空项目草稿中的文件，保存项目后生效。");
  }, []);

  const saveProject = useCallback(async (options: SaveProjectOptions = {}): Promise<ProjectRecord | null> => {
    if (!projectSlug) {
      setError("请先上传文件、导入项目或选择历史项目。");
      return null;
    }
    setIsSaving(true);
    setError("");
    setMessage("");
    try {
      let migrateExistingOutput = false;
      if (customOutputDirectory !== (savedProject?.custom_output_directory || "")) {
        const migrationInfo = await apiClient.checkOutputMigration(projectSlug, customOutputDirectory);
        if (migrationInfo.requires_migration) {
          migrateExistingOutput = window.confirm(
            `当前导出目录已有 ${migrationInfo.file_count} 个文件。是否迁移到新的导出目录？\n\n` +
              `旧目录：${migrationInfo.previous_output_directory}\n` +
              `新目录：${migrationInfo.new_output_directory}`
          );
        }
      }
      const project = await apiClient.saveProject(projectSlug, {
        project_name: projectName,
        uploaded_file_ids: uploadedFileIds,
        custom_output_directory_path: customOutputDirectory || undefined,
        migrate_existing_output: migrateExistingOutput,
        summary_output_format: options.summary_output_format,
        summary_batch_size: options.summary_batch_size,
        use_fine_grained_flow: options.use_fine_grained_flow
      });
      applyProject(project);
      setLastSavedAt(Date.now());
      await refreshProjects();
      return project;
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "保存项目失败";
      if (message.includes("输出目录") || message.includes("目录")) {
        setOutputDirectoryError(message);
      }
      setError(message);
      return null;
    } finally {
      setIsSaving(false);
    }
  }, [
    applyProject,
    customOutputDirectory,
    projectName,
    projectSlug,
    refreshProjects,
    savedProject,
    uploadedFileIds
  ]);

  const deleteProject = useCallback(
    async (slug: string) => {
      const targetSlug = slug || projectSlug;
      if (!targetSlug) {
        return;
      }
      try {
        const response = await apiClient.deleteProject(targetSlug);
        const deleteMessage = formatDeleteProjectMessage(response);
        if (targetSlug === projectSlug) {
          resetProjectState();
        }
        setMessage(deleteMessage);
        await refreshProjects();
      } catch (deleteError) {
        setError(deleteError instanceof Error ? deleteError.message : "删除项目失败");
      }
    },
    [projectSlug, refreshProjects, resetProjectState]
  );

  const importProjectFromDirectory = useCallback(
    async (path: string) => {
      if (!path) {
        return;
      }
      setError("");
      setMessage("");
      try {
        const project = await apiClient.importProject(path, workflowType);
        applyProject(project);
        setMessage("项目已导入，并已读取现有进度");
        void refreshProjects();
      } catch (importError) {
        setError(importError instanceof Error ? importError.message : "导入项目失败");
      }
    },
    [applyProject, refreshProjects, workflowType]
  );

  const validateOutputDirectory = useCallback(async () => {
    const value = outputDirectory.trim();
    const fallback = defaultOutputDirectory;
    if (!value) {
      setOutputDirectoryState(fallback);
      setOutputDirectoryError("");
      return;
    }
    if (!fallback || value === fallback.trim()) {
      setOutputDirectoryError("");
      return;
    }
    try {
      const resolved = await apiClient.resolvePath(value);
      if (resolved.resolved && resolved.is_directory) {
        setOutputDirectoryState(resolved.path);
        setOutputDirectoryError("");
        setError("");
        return;
      }
      setOutputDirectoryError("输出目录无效，请选择已有目录或使用默认输出目录。");
    } catch (validateError) {
      setOutputDirectoryError(
        validateError instanceof Error
          ? validateError.message
          : "输出目录无效，请选择已有目录或使用默认输出目录。"
      );
    }
  }, [defaultOutputDirectory, outputDirectory]);

  const useDefaultOutputDirectory = useCallback(async () => {
    setOutputDirectoryState(defaultOutputDirectory);
    setOutputDirectoryError("");
    setError("");
    if (!projectSlug) {
      return;
    }
    try {
      const project = await apiClient.useDefaultOutputDirectory(projectSlug);
      applyProject(project);
      setMessage("已切换到默认输出目录");
      await refreshProjects();
    } catch (fallbackError) {
      const message = fallbackError instanceof Error ? fallbackError.message : "切换默认输出目录失败";
      setOutputDirectoryError(message);
      setError(message);
    }
  }, [applyProject, defaultOutputDirectory, projectSlug, refreshProjects]);

  const openOutputDirectory = useCallback(async () => {
    if (!projectSlug) {
      setError("请先上传文件或选择历史项目，再打开输出目录。");
      return;
    }
    try {
      const response = await apiClient.openDirectory({
        project_slug: projectSlug
      });
      setOutputDirectoryState(response.path);
      setOutputDirectoryError("");
      setMessage("已请求打开输出目录");
    } catch (openError) {
      const message = openError instanceof Error ? openError.message : "打开目录失败";
      setOutputDirectoryError(message);
      setError(message);
    }
  }, [projectSlug]);

  return {
    projectName,
    setProjectName,
    projectSlug,
    defaultOutputDirectory,
    outputDirectory,
    setOutputDirectory,
    outputDirectoryError,
    setOutputDirectoryError,
    customOutputDirectory,
    uploadedFiles,
    uploadedFileIds,
    progress,
    projects,
    savedProject,
    warnings,
    isProjectDirty,
    canSaveProject,
    isUploading,
    isSaving,
    lastSavedAt,
    message,
    error,
    refreshProjects,
    refreshProjectState,
    restoreProject,
    startNewProject,
    deleteProject,
    uploadFiles,
    removeUploadedFile,
    clearUploadedFiles,
    saveProject,
    importProjectFromDirectory,
    validateOutputDirectory,
    useDefaultOutputDirectory,
    openOutputDirectory
  };
}
