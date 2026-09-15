import { useParams } from "react-router-dom";
import { NeutralBadge } from "../components/Badge";
import { RuleBlock } from "../components/RuleBlock";
import { ErrorState, Loading } from "../components/StateViews";
import { usePageCrumb } from "../contexts/PageMetaContext";
import { useRule } from "../hooks/useApi";
import { describeCondition } from "../utils/describeCondition";

export function RuleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const rule = useRule(id);
  usePageCrumb(rule.data?.rule_code);

  if (rule.isLoading) return <Loading label="Loading rule..." />;
  if (rule.isError || !rule.data) return <ErrorState message="Failed to load rule." />;

  const r = rule.data;

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow mono">{r.rule_code}</span>
        <h1>{r.title}</h1>
        <div className="tag-row" style={{ marginTop: 12 }}>
          <NeutralBadge>{r.rule_type}</NeutralBadge>
          <NeutralBadge>{r.jurisdiction}</NeutralBadge>
          <NeutralBadge>priority {r.priority}</NeutralBadge>
          <NeutralBadge>confidence {Math.round(r.confidence * 100)}%</NeutralBadge>
        </div>
      </div>

      <div className="section-title">Executable Logic</div>
      <RuleBlock conditions={r.conditions} actions={r.actions} sourceReference={r.source_reference} />

      <div className="section-title">Human-readable form</div>
      <div className="card">
        <p style={{ margin: 0, color: "var(--text-secondary)" }}>
          When <strong style={{ color: "var(--text-primary)" }}>{describeCondition(r.conditions)}</strong>
          , the outcome is <strong style={{ color: "var(--text-primary)" }}>{String(r.actions.verdict ?? "")}</strong>.
        </p>
      </div>

      {r.exceptions.length > 0 && (
        <>
          <div className="section-title">Exceptions ({r.exceptions.length})</div>
          {r.exceptions.map((e) => (
            <div className="card" key={e.id} style={{ borderLeft: "2px solid var(--warning)" }}>
              <p style={{ margin: 0 }}>{e.description}</p>
              <p className="text-muted mono" style={{ marginTop: 8, fontSize: 12 }}>
                {describeCondition(e.conditions)}
              </p>
              {e.source_reference && (
                <p className="text-muted mono" style={{ marginTop: 6, fontSize: 11.5 }}>
                  {e.source_reference}
                </p>
              )}
            </div>
          ))}
        </>
      )}

      <div className="section-title">Provenance</div>
      <div className="card">
        <dl className="kv-list">
          <dt>Source reference</dt>
          <dd className="mono">{r.source_reference ?? "—"}</dd>
          <dt>Source text</dt>
          <dd>{r.source_text ?? "—"}</dd>
          <dt>Effective from</dt>
          <dd>{r.effective_from}</dd>
          <dt>Effective to</dt>
          <dd>{r.effective_to ?? "open-ended"}</dd>
          <dt>Affected historical decisions</dt>
          <dd>{r.affected_decision_count}</dd>
        </dl>
      </div>
    </div>
  );
}
