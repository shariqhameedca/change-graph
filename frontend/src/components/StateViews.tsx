import type { ReactNode } from "react";
import { CircleAlert, Inbox } from "./icons";

export function Loading({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="state-block">
      <span className="spinner" /> <span style={{ marginLeft: 8 }}>{label}</span>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="error-block" style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <CircleAlert size={15} style={{ flexShrink: 0 }} />
      {message}
    </div>
  );
}

export function EmptyState({
  message,
  title,
  action,
}: {
  message: string;
  title?: string;
  action?: ReactNode;
}) {
  return (
    <div className="state-block">
      <Inbox size={26} className="state-block-icon" />
      {title && <div className="state-block-title">{title}</div>}
      <div>{message}</div>
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  );
}

/** A row of skeleton cells matching a table's shape, shown while data loads
 * instead of a blank area or spinner-only state. */
export function TableSkeleton({ columns = 5, rows = 6 }: { columns?: number; rows?: number }) {
  return (
    <div className="table-wrap">
      <table>
        <tbody>
          {Array.from({ length: rows }).map((_, r) => (
            <tr key={r}>
              {Array.from({ length: columns }).map((_, c) => (
                <td key={c}>
                  <div className="skeleton skeleton-row" style={{ width: c === 0 ? "70%" : "50%" }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card">
      <div className="skeleton skeleton-text" style={{ width: "40%", height: 16 }} />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton skeleton-text" style={{ width: `${85 - i * 12}%` }} />
      ))}
    </div>
  );
}

export function MetricSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="metric-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div className="metric-card" key={i}>
          <div className="skeleton skeleton-text" style={{ width: "60%" }} />
          <div className="skeleton skeleton-text" style={{ width: "40%", height: 28, marginTop: 8 }} />
        </div>
      ))}
    </div>
  );
}

export function GraphSkeleton() {
  return (
    <div className="graph-wrap" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 28 }}>
            <div
              className="skeleton"
              style={{ width: 84, height: 40, borderRadius: 8, animationDelay: `${i * 0.15}s` }}
            />
            {i < 3 && <div style={{ width: 24, height: 1.5, background: "var(--border-strong)" }} />}
          </div>
        ))}
      </div>
    </div>
  );
}
