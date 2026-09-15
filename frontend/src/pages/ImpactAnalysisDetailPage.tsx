import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { NeutralBadge, SeverityBadge, TransitionChip, VerdictBadge } from "../components/Badge";
import { GraphNodePanel } from "../components/GraphNodePanel";
import { GraphView } from "../components/GraphView";
import { MetricCard } from "../components/MetricCard";
import { EmptyState, ErrorState, GraphSkeleton, MetricSkeleton, TableSkeleton } from "../components/StateViews";
import { ArrowRight, GitCompareArrows, ListChecks, ShieldCheck, WorkflowIcon } from "../components/icons";
import { usePageCrumb } from "../contexts/PageMetaContext";
import {
  useDecisionChanges,
  useImpactAnalysis,
  useImpactGraph,
  useReEvaluateImpact,
  useVersionLookup,
} from "../hooks/useApi";
import type { GraphNode, Verdict } from "../types";

export function ImpactAnalysisDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const analysis = useImpactAnalysis(id);
  const graph = useImpactGraph(id);
  const decisionChanges = useDecisionChanges(id);
  const reEvaluate = useReEvaluateImpact();
  const versionLookup = useVersionLookup();
  const [showChangedOnly, setShowChangedOnly] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  usePageCrumb(analysis.data ? "Impact Report" : null);

  if (analysis.isLoading) {
    return (
      <div>
        <div className="page-header">
          <h1>Regulatory Impact</h1>
        </div>
        <MetricSkeleton />
        <GraphSkeleton />
      </div>
    );
  }
  if (analysis.isError || !analysis.data) return <ErrorState message="Failed to load impact analysis." />;

  const a = analysis.data;
  const s = a.summary;
  const rows = decisionChanges.data ?? [];
  const visibleRows = showChangedOnly ? rows.filter((r) => r.changed) : rows;

  const oldVersion = versionLookup.data?.get(a.compared_to_version_id);
  const newVersion = versionLookup.data?.get(a.regulation_version_id);
  const totalAffected =
    s.rules_affected + s.policies_affected + s.workflows_affected + s.decisions_changed;

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">Regulatory Impact</span>
        <h1>{newVersion?.regulation_name ?? "Regulatory Change Impact"}</h1>
        <div className="tag-row" style={{ marginTop: 14, alignItems: "center" }}>
          <NeutralBadge>{oldVersion?.version ?? "v1"}</NeutralBadge>
          <ArrowRight size={14} className="text-muted" />
          <NeutralBadge>{newVersion?.version ?? "v2"}</NeutralBadge>
        </div>
        <p className="page-subtitle">
          See which rules, policies, workflows, and decisions are affected by this change.
        </p>
      </div>

      <div className="metric-grid">
        <MetricCard label="Affected Entities" value={totalAffected} icon={<GitCompareArrows size={13} />} />
        <MetricCard label="Rules" value={s.rules_affected} icon={<ListChecks size={13} />} glow="danger" />
        <MetricCard label="Policies" value={s.policies_affected} icon={<ShieldCheck size={13} />} glow="cyan" />
        <MetricCard label="Workflows" value={s.workflows_affected} icon={<WorkflowIcon size={13} />} glow="success" />
        <MetricCard
          label="Decisions Changed"
          value={
            <>
              {s.decisions_changed}
              <span className="metric-unit">/ {s.decisions_affected}</span>
            </>
          }
          glow="accent"
        />
      </div>

      {s.decisions_affected > 0 && s.decisions_changed === 0 && a.status === "PENDING" && (
        <div className="card card-accent-line" style={{ marginBottom: 24, paddingLeft: 22 }}>
          <div className="flex-between">
            <div>
              <strong>{s.decisions_affected} historical decisions</strong> are candidates for
              re-evaluation under the new version.
            </div>
            <button className="btn btn-primary" disabled={reEvaluate.isPending} onClick={() => reEvaluate.mutate(a.id)}>
              {reEvaluate.isPending ? "Re-evaluating..." : "Re-evaluate Historical Decisions"}
            </button>
          </div>
        </div>
      )}

      <div className="section-title">Impact Graph</div>
      {graph.isLoading && <GraphSkeleton />}
      {graph.data && graph.data.nodes.length === 0 && <EmptyState message="No graph data available." />}
      {graph.data && graph.data.nodes.length > 0 && (
        <GraphView graph={graph.data} onNodeClick={(node) => setSelectedNode(node)} />
      )}
      {selectedNode && <GraphNodePanel node={selectedNode} onClose={() => setSelectedNode(null)} />}

      <div className="section-title">Impacted Entities</div>
      {a.items.length === 0 ? (
        <EmptyState message="No structural changes detected between these versions." />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Entity</th>
                <th>Change</th>
                <th>Severity</th>
                <th>Explanation</th>
              </tr>
            </thead>
            <tbody>
              {a.items.map((item) => (
                <tr key={item.id}>
                  <td className="mono">{item.entity_type}</td>
                  <td>
                    <NeutralBadge>{item.impact_type}</NeutralBadge>
                  </td>
                  <td>
                    <SeverityBadge severity={item.severity} />
                  </td>
                  <td className="text-secondary">{item.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="section-title-row" style={{ marginTop: 32, marginBottom: 14 }}>
        <div className="section-title" style={{ margin: 0 }}>
          Decision Explorer
        </div>
        <label style={{ fontSize: 12.5, display: "flex", alignItems: "center", gap: 6 }}>
          <input
            type="checkbox"
            checked={showChangedOnly}
            onChange={(e) => setShowChangedOnly(e.target.checked)}
          />
          Changed only
        </label>
      </div>

      {decisionChanges.isLoading && <TableSkeleton columns={5} />}
      {rows.length === 0 && !decisionChanges.isLoading && (
        <EmptyState message="Run re-evaluation to see affected historical decisions." />
      )}
      {visibleRows.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Record</th>
                <th>Jurisdiction</th>
                <th>Result</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row) => (
                <tr
                  key={row.new_decision_id}
                  className="clickable"
                  onClick={() => navigate(`/decisions/${row.new_decision_id}`)}
                >
                  <td className="mono">{row.record_reference}</td>
                  <td>{row.jurisdiction}</td>
                  <td>
                    {row.changed ? (
                      <TransitionChip from={row.old_verdict as Verdict} to={row.new_verdict as Verdict} />
                    ) : (
                      <VerdictBadge verdict={row.new_verdict} />
                    )}
                  </td>
                  <td className="text-secondary">{row.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
