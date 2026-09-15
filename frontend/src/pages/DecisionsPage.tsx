import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TransitionChip, VerdictBadge } from "../components/Badge";
import { EmptyState, ErrorState, TableSkeleton } from "../components/StateViews";
import { useDecisions, useRecords } from "../hooks/useApi";
import type { Verdict } from "../types";

export function DecisionsPage() {
  const decisions = useDecisions();
  const records = useRecords();
  const navigate = useNavigate();
  const [verdictFilter, setVerdictFilter] = useState<Verdict | "">("");
  const [jurisdictionFilter, setJurisdictionFilter] = useState("");
  const [changedOnly, setChangedOnly] = useState(false);

  const recordById = useMemo(() => new Map((records.data ?? []).map((r) => [r.id, r])), [records.data]);
  const decisionById = useMemo(() => new Map((decisions.data ?? []).map((d) => [d.id, d])), [decisions.data]);

  const jurisdictions = useMemo(
    () => Array.from(new Set((records.data ?? []).map((r) => r.jurisdiction))).sort(),
    [records.data]
  );

  const filtered = useMemo(() => {
    if (!decisions.data) return [];
    return decisions.data.filter((d) => {
      if (verdictFilter && d.verdict !== verdictFilter) return false;
      if (changedOnly && !d.changed_from_decision_id) return false;
      if (jurisdictionFilter) {
        const record = recordById.get(d.evaluation_record_id);
        if (record?.jurisdiction !== jurisdictionFilter) return false;
      }
      return true;
    });
  }, [decisions.data, verdictFilter, jurisdictionFilter, changedOnly, recordById]);

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">Decision Explorer</span>
        <h1>Decisions</h1>
        <p className="page-subtitle">
          Deterministic verdicts produced by the rule engine. Every decision is reproducible and
          traceable to source.
        </p>
      </div>

      <div className="filter-bar">
        <div className="field">
          <label>Status</label>
          <select value={verdictFilter} onChange={(e) => setVerdictFilter(e.target.value as Verdict | "")}>
            <option value="">All</option>
            <option value="PASS">PASS</option>
            <option value="FAIL">FAIL</option>
            <option value="REVIEW">REVIEW</option>
          </select>
        </div>
        <div className="field">
          <label>Jurisdiction</label>
          <select value={jurisdictionFilter} onChange={(e) => setJurisdictionFilter(e.target.value)}>
            <option value="">All</option>
            {jurisdictions.map((j) => (
              <option key={j} value={j}>
                {j}
              </option>
            ))}
          </select>
        </div>
        <div className="field" style={{ minWidth: "auto" }}>
          <label>Changed</label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, height: 34 }}>
            <input type="checkbox" checked={changedOnly} onChange={(e) => setChangedOnly(e.target.checked)} />
            <span style={{ fontSize: 13 }}>Only changed decisions</span>
          </label>
        </div>
        <div style={{ marginLeft: "auto", alignSelf: "center", color: "var(--text-muted)", fontSize: 12.5 }}>
          {filtered.length} of {decisions.data?.length ?? 0} decisions
        </div>
      </div>

      {decisions.isLoading && <TableSkeleton columns={5} />}
      {decisions.isError && <ErrorState message="Failed to load decisions." />}
      {filtered.length === 0 && decisions.data && (
        <EmptyState title="No matching decisions" message="Try adjusting the filters above." />
      )}

      {filtered.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Record</th>
                <th>Jurisdiction</th>
                <th>Verdict</th>
                <th>Summary</th>
                <th>Evaluated</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 300).map((d) => {
                const record = recordById.get(d.evaluation_record_id);
                const previous = d.changed_from_decision_id
                  ? decisionById.get(d.changed_from_decision_id)
                  : undefined;
                const changed = previous && previous.verdict !== d.verdict;
                return (
                  <tr key={d.id} className="clickable" onClick={() => navigate(`/decisions/${d.id}`)}>
                    <td className="mono">{record?.external_reference ?? d.evaluation_record_id.slice(0, 8)}</td>
                    <td>{record?.jurisdiction ?? "—"}</td>
                    <td>
                      {changed && previous ? (
                        <TransitionChip from={previous.verdict as Verdict} to={d.verdict as Verdict} />
                      ) : (
                        <VerdictBadge verdict={d.verdict} />
                      )}
                    </td>
                    <td className="text-secondary">{d.summary}</td>
                    <td className="text-muted">{new Date(d.evaluated_at).toLocaleString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
