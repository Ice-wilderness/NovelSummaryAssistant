import type { TaskRecord } from "../../api/types";
import type { StudioTone } from "./StudioPrimitives";

export function taskStatusLabel(status?: string) {
  switch (status) {
    case "pending":
      return "等待中";
    case "running":
      return "运行中";
    case "paused":
      return "已暂停";
    case "canceling":
      return "取消中";
    case "cancelled":
      return "已取消";
    case "success":
      return "已完成";
    case "partial_failed":
      return "部分结果";
    case "failed":
      return "失败";
    case "interrupted":
      return "已中断";
    default:
      return "空闲";
  }
}

export function taskStatusTone(status?: string): StudioTone {
  switch (status) {
    case "running":
    case "pending":
      return "primary";
    case "success":
      return "success";
    case "paused":
    case "canceling":
    case "partial_failed":
      return "warning";
    case "failed":
    case "interrupted":
      return "danger";
    case "cancelled":
      return "muted";
    default:
      return "neutral";
  }
}

export function taskTypeLabel(taskType?: string) {
  switch (taskType) {
    case "novel_summary":
      return "小说总结";
    case "small_summary_preparation":
      return "小总结准备";
    case "project_repair":
      return "项目修复";
    case "trigger_scan":
      return "雷点扫描";
    case "article_summary":
      return "文章总结";
    case "custom_summary":
      return "自定义总结";
    case "chapter_split":
      return "章节分割";
    case "model_fetch":
      return "模型列表";
    default:
      return taskType || "暂无任务";
  }
}

const bareStatusMessages = new Set([
  "cancelled",
  "failed",
  "interrupted",
  "partial_failed",
  "pending",
  "running",
  "success"
]);

function readableTaskMessage(message?: string | null) {
  const trimmed = message?.trim();
  if (!trimmed || bareStatusMessages.has(trimmed.toLowerCase())) {
    return "";
  }
  return trimmed;
}

export function taskHeadline(task: TaskRecord | null) {
  if (!task) {
    return "任务待命";
  }

  return (
    readableTaskMessage(task.progress_text) ||
    readableTaskMessage(task.result_summary) ||
    `${taskTypeLabel(task.task_type)}${taskStatusLabel(task.status)}`
  );
}

export function taskTerminalMessage(task: TaskRecord | null) {
  if (!task) {
    return "";
  }

  switch (task.status) {
    case "success":
      return readableTaskMessage(task.result_summary) || `${taskTypeLabel(task.task_type)}已完成`;
    case "failed":
      return readableTaskMessage(task.error) || `${taskTypeLabel(task.task_type)}失败`;
    case "partial_failed":
      return (
        readableTaskMessage(task.error) ||
        readableTaskMessage(task.result_summary) ||
        "任务部分完成，已保留可用结果"
      );
    case "cancelled":
      return "任务已取消";
    case "interrupted":
      return (
        readableTaskMessage(task.error) ||
        readableTaskMessage(task.warnings[0]) ||
        "后端重启前任务未结束，请重新启动或从项目进度继续"
      );
    default:
      return "";
  }
}
