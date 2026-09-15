import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { NeutralBadge } from "../components/Badge";
import { EmptyState, ErrorState, TableSkeleton } from "../components/StateViews";
import { ArrowRight, GitCompareArrows } from "../components/icons";
import {
  useCreateImpactAnalysis,
  useImpactAnalyses,
  useRegulationVersions,
  useRegulations,
} from "../hooks/useApi";

export function ImpactAnalysisListPage() {
  const analyses = useImpactAnalyses();
  const regulations = useRegulations();
  const navigate = useNavigate();
  const [regulationId, setRegulationId] = useState("");
  const [oldVersionId, setOldVersionId] = useState("");
  const [newVersionId, setNewVersionId] = useState("");
  const versions = useRegulationVersions(regulationId || undefined);
  const createAnalysis = useCreateImpactAnalysis();

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">Change Impact</span>
        <h1>Regulatory Change Impact</h1>
        <p className="page-subtitle">
          Compare two regulation versions to see which rules, policies, workflows, and decisions
          are affected.
        </p>
      </div>

      <div className="card card-elevated" style={{ marginBottom: 28 }}>
        <div className="section-title" style={{ marginTop: 0 }}>
          New Impact Analysis
        </div>
        <div className="form-grid">
          <div className="field">
            <label>Regulation</label>
            <select value={regulationId} onChange={(e) => setRegulationId(e.target.value)}>
              <option value="">Select...</option>
              {regulations.data?.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Old version</label>
            <select value={oldVersionId} onChange={(e) => setOldVersionId(e.target.value)}>
              <option value="">Select...</option>
              {versions.data?.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.version}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>New version</label>
            <select value={newVersionId} onChange={(e) => setNewVersionId(e.target.value)}>
              <option value="">Select...</option>
              {versions.data?.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.version}
                </option>
              ))}
            </select>
          </div>
        </div>
        <button
          className="btn btn-primary"
          disabled={!oldVersionId || !newVersionId || createAnalysis.isPending}
          onClick={() =>
            createAnalysis.mutate(
              { old_version_id: oldVersionId, new_version_id: newVersionId },
              { onSuccess: (a) => navigate(`/impact-analysis/${a.id}`) }
            )
          }
        >
          <GitCompareArrows size={14} />
          {createAnalysis.isPending ? "Analyzing..." : "Analyze Change"}
        </button>
        {createAnalysis.isError && <ErrorState message={(createAnalysis.error as Error).message} />}
      </div>

      <div className="section-title">Previous Analyses</div>
      {analyses.isLoading && <TableSkeleton columns={4} />}
      {analyses.isError && <ErrorState message="Failed to load impact analyses." />}
      {analyses.data && analyses.data.length === 0 && (
        <EmptyState
          title="No impact analysis yet"
          message="Compare two regulation versions above to discover downstream changes."
        />
      )}
      {analyses.data && analyses.data.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Created</th>
                <th>Status</th>
                <th>Rules Affected</th>
                <th>Decisions Changed</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {analyses.data.map((a) => (
                <tr key={a.id} className="clickable" onClick={() => navigate(`/impact-analysis/${a.id}`)}>
                  <td className="text-secondary">{new Date(a.created_at).toLocaleString()}</td>
                  <td>
                    <NeutralBadge>{a.status}</NeutralBadge>
                  </td>
                  <td>{a.summary.rules_affected}</td>
                  <td>{a.summary.decisions_changed}</td>
                  <td>
                    <ArrowRight size={14} className="text-muted" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
