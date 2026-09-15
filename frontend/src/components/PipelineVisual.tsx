import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  FileStack,
  ListChecks,
  ScrollText,
  ShieldCheck,
  WorkflowIcon,
} from "./icons";

const STAGES = [
  { label: "Regulation", sub: "Source text", icon: FileStack, color: "#7c5cff" },
  { label: "Definitions", sub: "Defined terms", icon: BookOpen, color: "#22d3ee" },
  { label: "Rules", sub: "Executable logic", icon: ScrollText, color: "#ef4444" },
  { label: "Policies", sub: "Internal controls", icon: ShieldCheck, color: "#a78bfa" },
  { label: "Workflows", sub: "Business process", icon: WorkflowIcon, color: "#22c55e" },
  { label: "Decisions", sub: "Deterministic verdicts", icon: CheckCircle2, color: "#f59e0b" },
];

/** The core "regulation is a connected system" visual -- used on the
 * Overview page to communicate the product's idea within seconds. */
export function PipelineVisual() {
  return (
    <div className="pipeline">
      {STAGES.map((stage, i) => {
        const Icon = stage.icon;
        return (
          <div style={{ display: "contents" }} key={stage.label}>
            <div className="pipeline-node" style={{ ["--node-color" as string]: stage.color }}>
              <div className="pipeline-node-icon">
                <Icon size={17} />
              </div>
              <div className="pipeline-node-label">{stage.label}</div>
              <div className="pipeline-node-sub">{stage.sub}</div>
            </div>
            {i < STAGES.length - 1 && (
              <div className="pipeline-arrow">
                <ArrowRight size={16} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function MiniPipeline({ activeIndex }: { activeIndex?: number }) {
  return (
    <div className="pipeline" style={{ padding: 0 }}>
      {STAGES.map((stage, i) => (
        <div style={{ display: "contents" }} key={stage.label}>
          <div
            className="pipeline-node"
            style={{
              ["--node-color" as string]: stage.color,
              padding: "10px 6px",
              opacity: activeIndex === undefined || activeIndex === i ? 1 : 0.45,
            }}
          >
            <div className="pipeline-node-label" style={{ fontSize: 11 }}>
              {stage.label}
            </div>
          </div>
          {i < STAGES.length - 1 && (
            <div className="pipeline-arrow" style={{ paddingTop: 0 }}>
              <ArrowRight size={13} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
