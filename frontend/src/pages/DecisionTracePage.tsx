import { useState } from "react";
import { useParams } from "react-router-dom";
import { VerdictBadge } from "../components/Badge";
import { ErrorState, Loading } from "../components/StateViews";
import { Timeline, TimelineItem } from "../components/Timeline";
import { ChevronDown, Scale } from "../components/icons";
import { usePageCrumb } from "../contexts/PageMetaContext";
import { useDecision } from "../hooks/useApi";
import type { DecisionTrace } from "../types";

export function DecisionTracePage() {
  const { id } = useParams<{ id: string }>();
  const decision = useDecision(id);
  usePageCrumb(decision.data ? `Trace #${decision.data.id.slice(0, 8)}` : null);

  if (decision.isLoading) return <Loading label="Loading decision trace..." />;
  if (decision.isError || !decision.data) return <ErrorState message="Failed to load decision." />;

  const d = decision.data;
  const firedTraces = d.trace.filter((t) => t.evaluation_result === "MATCH");
  const otherTraces = d.trace.filter((t) => t.evaluation_result !== "MATCH");

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">Decision Trace</span>
        <h1>#{d.id.slice(0, 8)}</h1>
        <p className="page-subtitle">
          Every verdict is reproducible and traceable to the rule and source that produced it.
        </p>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="flex-between">
          <div>
            <div className="text-muted mono" style={{ fontSize: 11 }}>
              VERDICT
            </div>
            <div style={{ marginTop: 8 }}>
              <VerdictBadge verdict={d.verdict} />
            </div>
          </div>
          <dl className="kv-list" style={{ textAlign: "right" }}>
            <dt>Evaluated</dt>
            <dd>{new Date(d.evaluated_at).toLocaleString()}</dd>
            <dt>Engine version</dt>
            <dd className="mono">{d.engine_version}</dd>
          </dl>
        </div>
        <p style={{ marginTop: 14, color: "var(--text-secondary)" }}>{d.summary}</p>
      </div>

      <div className="section-title">Input Record</div>
      <div className="card">
        <pre className="pre-block">{JSON.stringify(d.trace[0]?.input_snapshot ?? {}, null, 2)}</pre>
      </div>

      {firedTraces.length > 0 && (
        <>
          <div className="section-title">Rules Triggered ({firedTraces.length})</div>
          {firedTraces.map((t) => (
            <TraceChain key={t.id} trace={t} verdict={d.verdict} />
          ))}
        </>
      )}

      {otherTraces.length > 0 && (
        <>
          <div className="section-title">Other Applicable Rules ({otherTraces.length})</div>
          {otherTraces.map((t) => (
            <OtherTraceRow key={t.id} trace={t} />
          ))}
        </>
      )}
    </div>
  );
}

interface LeafResult {
  field: string;
  operator: string;
  expected: unknown;
  actual: unknown;
  result: boolean;
}

/** The engine's condition_result tree mirrors the (possibly nested)
 * all/any/not condition shape -- most real rules are an `all` wrapper, so
 * the top-level node itself is never a leaf. This walks the tree to find
 * the specific leaf worth surfacing: the one that caused a mismatch if
 * there is one, otherwise the most specific (last) leaf checked. */
function findKeyLeaf(node: unknown): LeafResult | null {
  if (!node || typeof node !== "object") return null;
  const obj = node as Record<string, unknown>;

  if (typeof obj.field === "string") {
    return obj as unknown as LeafResult;
  }

  const branches: unknown[] = Array.isArray(obj.all)
    ? obj.all
    : Array.isArray(obj.any)
    ? obj.any
    : obj.not
    ? [obj.not]
    : [];

  const leaves = branches.map(findKeyLeaf).filter((l): l is LeafResult => l !== null);
  if (leaves.length === 0) return null;
  return leaves.find((l) => !l.result) ?? leaves[leaves.length - 1];
}

function TraceChain({ trace, verdict }: { trace: DecisionTrace; verdict: string }) {
  const conditionTree = trace.condition_results?.condition_result;
  const conditionResult = findKeyLeaf(conditionTree);
  const [sourceOpen, setSourceOpen] = useState(false);

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <Timeline>
        <TimelineItem label="Rule" tone={verdict === "FAIL" ? "fail" : "accent"} icon={<Scale size={11} />}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span className="mono text-accent" style={{ fontSize: 12.5 }}>
              {trace.rule_code}
            </span>
            <strong>{trace.rule_title}</strong>
          </div>
          <p className="text-secondary" style={{ marginTop: 6, marginBottom: 0, fontSize: 13 }}>
            {trace.explanation}
          </p>
        </TimelineItem>

        {conditionResult?.field && (
          <>
            <TimelineItem label="Condition">
              <div className="mono" style={{ fontSize: 13 }}>
                <span className="rule-field">{conditionResult.field}</span>{" "}
                <span className="rule-op">{conditionResult.operator}</span>{" "}
                <span className="rule-value">{JSON.stringify(conditionResult.expected)}</span>
              </div>
            </TimelineItem>
            <TimelineItem label="Input" tone={verdict === "FAIL" ? "fail" : "pass"}>
              <div className="mono" style={{ fontSize: 13 }}>
                {conditionResult.field} = <strong>{JSON.stringify(conditionResult.actual)}</strong>
              </div>
            </TimelineItem>
          </>
        )}

        {trace.source_reference && (
          <TimelineItem label="Regulatory Source">
            <button
              className="btn btn-ghost btn-sm"
              style={{ padding: "3px 0" }}
              onClick={() => setSourceOpen((v) => !v)}
            >
              <span className="mono">{trace.source_reference}</span>
              <ChevronDown size={13} style={{ transform: sourceOpen ? "rotate(180deg)" : undefined, transition: "transform 0.15s" }} />
            </button>
            {sourceOpen && <p className="pre-block" style={{ marginTop: 8 }}>{trace.source_text}</p>}
          </TimelineItem>
        )}
      </Timeline>
    </div>
  );
}

function OtherTraceRow({ trace }: { trace: DecisionTrace }) {
  const badgeClass = trace.evaluation_result === "EXCEPTED" ? "badge-neutral" : "badge-pass";
  return (
    <div className="card" style={{ padding: "12px 16px" }}>
      <div className="flex-between">
        <div>
          <span className="mono text-secondary" style={{ fontSize: 12 }}>
            {trace.rule_code}
          </span>{" "}
          {trace.rule_title}
        </div>
        <span className={`badge ${badgeClass}`}>{trace.evaluation_result}</span>
      </div>
    </div>
  );
}
