import type { Verdict } from "../types";

export function VerdictBadge({ verdict }: { verdict: string }) {
  const cls =
    verdict === "PASS" ? "badge-pass" : verdict === "FAIL" ? "badge-fail" : "badge-review";
  return (
    <span className={`badge ${cls}`}>
      <span className="badge-dot" />
      {verdict}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === "HIGH" ? "badge-high" : severity === "MEDIUM" ? "badge-medium" : "badge-low";
  return (
    <span className={`badge ${cls}`}>
      <span className="badge-dot" />
      {severity}
    </span>
  );
}

export function NeutralBadge({ children }: { children: React.ReactNode }) {
  return <span className="badge badge-neutral">{children}</span>;
}

export function AccentBadge({ children }: { children: React.ReactNode }) {
  return <span className="badge badge-accent">{children}</span>;
}

export function CyanBadge({ children }: { children: React.ReactNode }) {
  return <span className="badge badge-cyan">{children}</span>;
}

/** The strong "PASS -> FAIL" style indicator used wherever a verdict
 * changed between two decisions -- this should read as unmissable. */
export function TransitionChip({ from, to }: { from: Verdict; to: Verdict }) {
  return (
    <span className="transition-chip">
      {from}
      <span className="arrow">&rarr;</span>
      {to}
    </span>
  );
}

export function ChangedFlag() {
  return <span className="changed-flag">Changed</span>;
}
