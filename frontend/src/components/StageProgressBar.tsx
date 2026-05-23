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
  const visibleStages = useMemo(
    () => stages.filter((s) => s.total === null || s.total > 0),
    [stages]
  );

  if (visibleStages.length === 0) return null;

  return (
    <div className="stage-progress-bar" role="progressbar">
      {visibleStages.map((stage) => {
        const isRunning = stage.id === currentStage || stage.status === "running";
        const isCompleted = stage.status === "completed";
        const isPending = !isCompleted && !isRunning;
        const totalText = stage.total !== null ? String(stage.total) : "?";
        const fraction =
          stage.total !== null ? `${stage.completed}/${totalText}` : totalText;
        const fillPct =
          stage.total && stage.total > 0
            ? Math.min(100, Math.round((stage.completed / stage.total) * 100))
            : isCompleted
            ? 100
            : 0;

        return (
          <div
            key={stage.id}
            className={classNames(
              "stage-segment",
              isCompleted && "stage-completed",
              isRunning && "stage-running",
              isPending && "stage-pending"
            )}
          >
            <div className="stage-fill-track">
              <div
                className={classNames(
                  "stage-fill-bar",
                  isRunning && "stage-fill-animated"
                )}
                style={{ width: `${fillPct}%` }}
              />
            </div>
            <div className="stage-meta">
              <span className="stage-label">{stage.label}</span>
              <span className="stage-count">
                {isCompleted ? <span className="stage-check">&#10003;</span> : fraction}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
