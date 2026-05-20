import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type { ProjectRecord, UploadedFileRef, WorkflowType } from "../api/types";

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
  const [customOutputDirectory, setCustomOutputDirectory] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRef[]>([]);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const uploadedFileIds = useMemo(
    () => uploadedFiles.filter((file) => !file.missing).map((file) => file.id),
    [uploadedFiles]
  );
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
    setCustomOutputDirectory(project.custom_output_directory || "");
    setUploadedFiles(project.uploads);
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
        setDefaultOutputDirectory(response.workflow_output_directory);
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

  const openDefaultDirectory = useCallback(async () => {
    if (!projectSlug) {
      setError("请先上传文件或选择历史项目，再打开默认导出目录。");
      return;
    }
    try {
      const response = await apiClient.openDirectory({
        project_slug: projectSlug,
        workflow_type: workflowType
      });
      setDefaultOutputDirectory(response.path);
      setMessage("已请求打开默认导出目录");
    } catch (openError) {
      setError(openError instanceof Error ? openError.message : "打开目录失败");
    }
  }, [projectSlug, workflowType]);

  const openCustomDirectory = useCallback(async () => {
    if (!customOutputDirectory.trim()) {
      setError("请先选择自定义输出目录。");
      return;
    }
    try {
      await apiClient.openDirectory({ path: customOutputDirectory });
      setMessage("已请求打开自定义输出目录");
    } catch (openError) {
      setError(openError instanceof Error ? openError.message : "打开目录失败");
    }
  }, [customOutputDirectory]);

  return {
    projectName,
    setProjectName,
    projectSlug,
    defaultOutputDirectory,
    customOutputDirectory,
    setCustomOutputDirectory,
    uploadedFiles,
    uploadedFileIds,
    projects,
    warnings,
    isUploading,
    message,
    error,
    refreshProjects,
    restoreProject,
    uploadFiles,
    removeUploadedFile,
    openDefaultDirectory,
    openCustomDirectory
  };
}
