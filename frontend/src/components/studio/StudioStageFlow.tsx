import { useMemo } from "react";
import { motion } from "framer-motion";
import type { TaskRecord } from "../../api/types";
import type { Stage } from "../StageProgressBar";
import { StudioStatusBadge } from "./StudioPrimitives";
import { taskStatusLabel, taskStatusTone, taskTypeLabel } from "./taskPresentation";

interface StudioStageFlowProps {
  task: TaskRecord | null;
}

interface StudioStageItem {
  id: string;
  label: string;
  completed: number;
  total: number | null;
  status: "completed" | "running" | "pending";
}

const activeStatuses = new Set(["pending", "running", "paused", "canceling"]);
const terminalStatuses = new Set(["success", "partial_failed", "failed", "cancelled", "interrupted"]);

function latestEventStages(task: TaskRecord | null) {
  if (!task) {
    return { stages: [] as StudioStageItem[], currentStage: "" };
  }

  for (let index = task.events.length - 1; index >= 0; index -= 1) {
    const event = task.events[index];
    if (event.event_type !== "progress" || !Array.isArray(event.data.stages)) {
      continue;
    }

    return {
      stages: (event.data.stages as Stage[]).map((stage) => ({
        id: stage.id,
        label: stage.label,
        completed: stage.completed,
        total: stage.total,
        status: stage.status
      })),
      currentStage: typeof event.data.current_stage === "string" ? event.data.current_stage : ""
    };
  }

  return { stages: [] as StudioStageItem[], currentStage: "" };
}

function lifecycleStages(task: TaskRecord | null): StudioStageItem[] {
  if (!task) {
    return [];
  }

  const isActive = activeStatuses.has(task.status);
  const isTerminal = terminalStatuses.has(task.status);
  const isPending = task.status === "pending";

  return [
    {
      id: "prepare",
      label: "准备",
      completed: isPending ? 0 : 1,
      total: 1,
      status: isPending ? "running" : "completed"
    },
    {
      id: "execute",
      label: "执行",
      completed: isTerminal ? 1 : 0,
      total: 1,
      status: isActive && !isPending ? "running" : isTerminal ? "completed" : "pending"
    },
    {
      id: "settle",
      label: "收束",
      completed: isTerminal ? 1 : 0,
      total: 1,
      status: isTerminal ? "completed" : "pending"
    },
    {
      id: "finish",
      label: "归档",
      completed: task.status === "success" || task.status === "partial_failed" ? 1 : 0,
      total: 1,
      status: task.status === "success" || task.status === "partial_failed" ? "completed" : "pending"
    }
  ];
}

function stageFill(stage: StudioStageItem) {
  if (stage.status === "completed") {
    return 100;
  }
  if (!stage.total || stage.total <= 0) {
    return stage.status === "running" ? 42 : 0;
  }
  return Math.max(0, Math.min(100, Math.round((stage.completed / stage.total) * 100)));
}

export function StudioStageFlow({ task }: StudioStageFlowProps) {
  const { stages, currentStage } = useMemo(() => {
    const eventStageState = latestEventStages(task);
    return eventStageState.stages.length > 0
      ? eventStageState
      : { stages: lifecycleStages(task), currentStage: "" };
  }, [task]);

  return (
    <section className="studio-stage-flow" aria-label="任务阶段流">
      <div className="studio-stage-flow__header">
        <div>
          <span>Stage Flow</span>
          <strong>{task ? taskTypeLabel(task.task_type) : "等待工作流"}</strong>
        </div>
        <StudioStatusBadge tone={taskStatusTone(task?.status)}>
          {task ? `阶段：${taskStatusLabel(task.status)}` : "阶段待命"}
        </StudioStatusBadge>
      </div>

      {stages.length === 0 ? (
        <div className="studio-stage-flow__empty">
          <span>暂无运行任务</span>
          <small>启动总结、分割或扫描后，这里会显示当前阶段。</small>
        </div>
      ) : (
        <div className="studio-stage-flow__track">
          {stages.map((stage, index) => {
            const isRunning = stage.status === "running" || stage.id === currentStage;
            const fill = stageFill(stage);
            return (
              <motion.div
                animate={{ opacity: 1, y: 0 }}
                className={`studio-stage-node studio-stage-node--${stage.status} ${isRunning ? "studio-stage-node--active" : ""}`}
                initial={{ opacity: 0, y: 8 }}
                key={stage.id}
                transition={{ delay: index * 0.035, duration: 0.24 }}
              >
                <div className="studio-stage-node__bar">
                  <motion.span
                    animate={{ width: `${fill}%` }}
                    transition={{ duration: 0.36, ease: [0.22, 1, 0.36, 1] }}
                  />
                </div>
                <div className="studio-stage-node__meta">
                  <strong>{stage.label}</strong>
                  <small>
                    {stage.total !== null ? `${stage.completed}/${stage.total}` : isRunning ? "进行中" : "待定"}
                  </small>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </section>
  );
}
