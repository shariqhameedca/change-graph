import type { ReactNode } from "react";

export function Timeline({ children }: { children: ReactNode }) {
  return <div className="timeline">{children}</div>;
}

export function TimelineItem({
  label,
  tone = "neutral",
  icon,
  children,
}: {
  label: string;
  tone?: "neutral" | "pass" | "fail" | "accent";
  icon?: ReactNode;
  children: ReactNode;
}) {
  const nodeClass =
    tone === "fail"
      ? "timeline-node node-fail"
      : tone === "pass"
      ? "timeline-node node-pass"
      : tone === "accent"
      ? "timeline-node node-accent"
      : "timeline-node";

  return (
    <div className="timeline-item">
      <div className={nodeClass}>{icon}</div>
      <div className="timeline-label">{label}</div>
      {children}
    </div>
  );
}
