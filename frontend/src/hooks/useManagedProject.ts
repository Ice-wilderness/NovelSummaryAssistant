import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { ProjectProgress, ProjectRecord, UploadedFileRef, WorkflowType } from "../api/types";

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

export function useManagedProject(workflowType: WorkflowType) {
  const [projectName, setProjectName] = useState("");
  const [projectSlug, setProjectSlug] = useState("");
  const [defaultOutputDirectory, setDefaultOutputDirectory] = useState("");
  const [outputDirectory, setOutputDirectory] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRef[]>([]);
  const [progress, setProgress] = useState<ProjectProgress | null>(null);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [isUploading, setIsUploading] = useState(false);
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
    () => uploadedFiles.filter((file) => file.missing).map((file) => `${file.original_name} 已缺失`),
    [uploadedFiles]
  );

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
    setOutputDirectory(project.custom_output_directory || project.default_output_directory);
    setUploadedFiles(project.uploads);
    setProgress(project.progress);
    setMessage(project.latest_task_status ? `最近任务：${project.latest_task_status}` : "");
    setError(project.warnings?.[0] || "");
  }, []);

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
        const uploadFiles = await Promise.all(
          files.map(async (file) => ({
            name: file.name,
            content: await file.text()
          }))
        );
        const response = await apiClient.uploadTextFiles(
          effectiveProjectName,
          workflowType,
          uploadFiles,
          projectSlug
        );
        applyProject(response.project);
        if (!response.project.custom_output_directory) {
          setOutputDirectory(response.workflow_output_directory);
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
  }, []);

  const clearUploadedFiles = useCallback(async () => {
    if (!projectSlug) {
      setUploadedFiles([]);
      return;
    }
    try {
      const project = await apiClient.clearProjectUploads(projectSlug);
      applyProject(project);
      setMessage("已清空当前项目的上传文件");
      void refreshProjects();
    } catch (clearError) {
      setError(clearError instanceof Error ? clearError.message : "清空文件失败");
    }
  }, [applyProject, projectSlug, refreshProjects]);

  const saveProjectName = useCallback(async () => {
    if (!projectSlug) {
      setError("请先上传文件、导入项目或选择历史项目。");
      return;
    }
    try {
      const project = await apiClient.updateProjectName(projectSlug, projectName);
      applyProject(project);
      setMessage("项目名称已保存");
      void refreshProjects();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存项目名称失败");
    }
  }, [applyProject, projectName, projectSlug, refreshProjects]);

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
      setOutputDirectory(fallback);
      return;
    }
    if (!fallback || value === fallback.trim()) {
      return;
    }
    try {
      const resolved = await apiClient.resolvePath(value);
      if (resolved.resolved && resolved.is_directory) {
        setOutputDirectory(resolved.path);
        setError("");
        return;
      }
      setOutputDirectory(fallback);
      setError("输出目录无效，已恢复为项目默认输出目录。");
    } catch (validateError) {
      setOutputDirectory(fallback);
      setError(validateError instanceof Error ? validateError.message : "输出目录无效，已恢复为项目默认输出目录。");
    }
  }, [defaultOutputDirectory, outputDirectory]);

  const useDefaultOutputDirectory = useCallback(() => {
    setOutputDirectory(defaultOutputDirectory);
    setError("");
  }, [defaultOutputDirectory]);

  const openOutputDirectory = useCallback(async () => {
    if (!projectSlug) {
      setError("请先上传文件或选择历史项目，再打开输出目录。");
      return;
    }
    try {
      const response = await apiClient.openDirectory({
        project_slug: projectSlug,
        workflow_type: workflowType,
        custom_output_directory_path: customOutputDirectory
      });
      setOutputDirectory(response.path);
      setMessage("已请求打开输出目录");
    } catch (openError) {
      setError(openError instanceof Error ? openError.message : "打开目录失败");
    }
  }, [customOutputDirectory, projectSlug, workflowType]);

  return {
    projectName,
    setProjectName,
    projectSlug,
    defaultOutputDirectory,
    outputDirectory,
    setOutputDirectory,
    customOutputDirectory,
    uploadedFiles,
    uploadedFileIds,
    progress,
    projects,
    warnings,
    isUploading,
    message,
    error,
    refreshProjects,
    restoreProject,
    uploadFiles,
    removeUploadedFile,
    clearUploadedFiles,
    saveProjectName,
    importProjectFromDirectory,
    validateOutputDirectory,
    useDefaultOutputDirectory,
    openOutputDirectory
  };
}
