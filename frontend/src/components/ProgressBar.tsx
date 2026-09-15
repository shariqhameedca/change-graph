import type { CompileJobStatus } from "../types";

const STATUS_LABEL: Record<CompileJobStatus, string> = {
  QUEUED: "Queued",
  RUNNING: "Extracting",
  SUCCEEDED: "Complete",
  FAILED: "Failed",
  COMPLETED_WITH_WARNINGS: "Complete, with warnings",
  CANCELLED: "Cancelled",
};

function fillClass(status: CompileJobStatus): string | undefined {
  if (status === "SUCCEEDED") return "is-success";
  if (status === "FAILED") return "is-danger";
  if (status === "COMPLETED_WITH_WARNINGS") return "is-warning";
  return undefined;
}

/** A determinate progress bar for a chunked compile job -- distinct from the
 * generic `.spinner` (indeterminate) used elsewhere for actions with no
 * natural progress signal. */
export function ProgressBar({
  completed,
  total,
  status,
  label,
}: {
  completed: number;
  total: number;
  status: CompileJobStatus;
  label?: string;
}) {
  const pct = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;
  return (
    <div>
      <div className="progress-track">
        <div
          className={`progress-fill ${fillClass(status) ?? ""}`.trim()}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="progress-meta">
        <span className="text-muted">{label ?? STATUS_LABEL[status]}</span>
        <span className="text-muted mono">
          {total > 0 ? `Chunk ${completed} of ${total}` : ""}
        </span>
      </div>
    </div>
  );
}
