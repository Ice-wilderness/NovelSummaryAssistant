import { useMemo } from "react";

export interface Stage {
  id: string;
  label: string;
  completed: number;
  total: number | null;
  status: "completed" | "running" | "pending";
}

interface StageProgressBarProps {
  stages: Stage[];
  currentStage: string;
}

function classNames(...values: Array<string | false | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function StageProgressBar({ stages, currentStage }: StageProgressBarProps) {
  const visibleStages = useMemo(() => stages.filter((s) => s.total === null || s.total > 0), [stages]);

  if (visibleStages.length === 0) return null;

  return (
    <div className="stage-progress-bar">
      {visibleStages.map((stage, index) => {
        const isRunning = stage.id === currentStage || stage.status === "running";
        const isCompleted = stage.status === "completed";
        const totalText = stage.total !== null ? String(stage.total) : "?";
        const fraction = stage.total ? `${stage.completed}/${totalText}` : totalText;

        return (
          <div
            key={stage.id}
            className={classNames(
              "stage-segment",
              isCompleted && "stage-completed",
              isRunning && !isCompleted && "stage-running",
              !isCompleted && !isRunning && "stage-pending"
            )}
            style={{ flex: stage.total ? stage.total : 1 }}
          >
            <span className="stage-label">{stage.label}</span>
            <span className="stage-count">
              {isCompleted ? (
                <span className="stage-check">&#10003;</span>
              ) : (
                fraction
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
