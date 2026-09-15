import { Link, useNavigate } from "react-router-dom";
import { NeutralBadge } from "../components/Badge";
import { EmptyState, ErrorState, CardSkeleton } from "../components/StateViews";
import { Plus } from "../components/icons";
import { useDefinitions, useRegulationVersions, useRegulations, useRules } from "../hooks/useApi";
import type { Regulation } from "../types";

function RegulationCard({ regulation }: { regulation: Regulation }) {
  const navigate = useNavigate();
  const versions = useRegulationVersions(regulation.id);
  const current = versions.data
    ?.slice()
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .at(-1);
  const rules = useRules(current?.id);
  const definitions = useDefinitions(regulation.id, current?.id);

  return (
    <div className="card card-interactive" onClick={() => navigate(`/regulations/${regulation.id}`)}>
      <div className="flex-between" style={{ alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <strong style={{ fontSize: 15 }}>{regulation.name}</strong>
        </div>
        {current && (
          <span className={`badge ${current.status === "ACTIVE" ? "badge-pass" : "badge-neutral"}`}>
            <span className="badge-dot" />
            {current.status}
          </span>
        )}
      </div>

      <div className="tag-row" style={{ marginTop: 10 }}>
        <NeutralBadge>{regulation.jurisdiction}</NeutralBadge>
        <NeutralBadge>{versions.data?.length ?? 0} version(s)</NeutralBadge>
      </div>

      <div style={{ display: "flex", gap: 22, marginTop: 18 }}>
        <div>
          <div className="metric-label" style={{ fontSize: 10 }}>
            Rules
          </div>
          <div style={{ fontSize: 20, fontWeight: 650, marginTop: 2 }}>{rules.data?.length ?? "—"}</div>
        </div>
        <div>
          <div className="metric-label" style={{ fontSize: 10 }}>
            Definitions
          </div>
          <div style={{ fontSize: 20, fontWeight: 650, marginTop: 2 }}>{definitions.data?.length ?? "—"}</div>
        </div>
      </div>

      <div
        style={{
          marginTop: 16,
          paddingTop: 14,
          borderTop: "1px solid var(--border)",
          display: "flex",
          justifyContent: "space-between",
          fontSize: 12,
        }}
      >
        <div>
          <div className="text-muted">Latest version</div>
          <div className="mono" style={{ marginTop: 3, color: "var(--text-primary)" }}>
            {current?.version ?? "—"}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="text-muted">Effective</div>
          <div style={{ marginTop: 3 }}>{current?.effective_from ?? "—"}</div>
        </div>
      </div>
    </div>
  );
}

export function RegulationsPage() {
  const regulations = useRegulations();

  return (
    <div>
      <div className="page-header flex-between">
        <div>
          <span className="page-eyebrow">Source Documents</span>
          <h1>Regulations</h1>
          <p className="page-subtitle">Source regulations compiled into executable knowledge.</p>
        </div>
        <Link className="btn btn-primary" to="/regulations/new">
          <Plus size={14} />
          New Regulation
        </Link>
      </div>

      {regulations.isLoading && (
        <div className="regulation-grid">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      )}
      {regulations.isError && <ErrorState message="Failed to load regulations." />}
      {regulations.data && regulations.data.length === 0 && (
        <EmptyState
          title="No regulations yet"
          message="Add your first regulation to start compiling it into executable rules."
          action={
            <Link className="btn btn-primary" to="/regulations/new">
              New Regulation
            </Link>
          }
        />
      )}
      {regulations.data && regulations.data.length > 0 && (
        <div className="regulation-grid">
          {regulations.data.map((r) => (
            <RegulationCard key={r.id} regulation={r} />
          ))}
        </div>
      )}
    </div>
  );
}
