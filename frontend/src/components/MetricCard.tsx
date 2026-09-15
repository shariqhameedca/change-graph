import type { ReactNode } from "react";

export function MetricCard({
  label,
  value,
  unit,
  icon,
  glow,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  icon?: ReactNode;
  glow?: "accent" | "cyan" | "success" | "danger" | "warning";
}) {
  const glowVar =
    glow === "cyan"
      ? "var(--cyan-soft)"
      : glow === "success"
      ? "var(--success-soft)"
      : glow === "danger"
      ? "var(--danger-soft)"
      : glow === "warning"
      ? "var(--warning-soft)"
      : "var(--accent-soft)";

  return (
    <div className="metric-card" style={{ ["--metric-glow" as string]: glowVar }}>
      <div className="metric-label">
        {icon}
        {label}
      </div>
      <div className="metric-value">
        {value}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
    </div>
  );
}
