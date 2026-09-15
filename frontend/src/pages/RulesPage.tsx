import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { NeutralBadge } from "../components/Badge";
import { EmptyState, ErrorState, TableSkeleton } from "../components/StateViews";
import { ArrowRight, FlaskConical } from "../components/icons";
import { useRules, useVersionLookup } from "../hooks/useApi";
import { previewCondition } from "../utils/ruleCondition";

export function RulesPage() {
  const rules = useRules();
  const versionLookup = useVersionLookup();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [jurisdictionFilter, setJurisdictionFilter] = useState("");
  const [regulationFilter, setRegulationFilter] = useState("");

  const jurisdictions = useMemo(
    () => Array.from(new Set(rules.data?.map((r) => r.jurisdiction) ?? [])).sort(),
    [rules.data]
  );

  const regulations = useMemo(() => {
    if (!versionLookup.data) return [];
    const byId = new Map<string, string>();
    versionLookup.data.forEach((v) => byId.set(v.regulation_id, v.regulation_name));
    return Array.from(byId.entries())
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [versionLookup.data]);

  const filtered = useMemo(() => {
    if (!rules.data) return [];
    return rules.data.filter((r) => {
      const matchesSearch =
        !search ||
        r.rule_code.toLowerCase().includes(search.toLowerCase()) ||
        r.title.toLowerCase().includes(search.toLowerCase());
      const matchesJurisdiction = !jurisdictionFilter || r.jurisdiction === jurisdictionFilter;
      const matchesRegulation =
        !regulationFilter ||
        versionLookup.data?.get(r.regulation_version_id)?.regulation_id === regulationFilter;
      return matchesSearch && matchesJurisdiction && matchesRegulation;
    });
  }, [rules.data, search, jurisdictionFilter, regulationFilter, versionLookup.data]);

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">Executable Knowledge</span>
        <h1>Rules</h1>
        <p className="page-subtitle">
          Every rule compiled from regulatory text, expressed as executable conditions and
          actions -- not prose.
        </p>
      </div>

      <div className="filter-bar">
        <div className="field">
          <label>Search</label>
          <input
            placeholder="RULE-017 or title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ minWidth: 220 }}
          />
        </div>
        <div className="field">
          <label>Regulation</label>
          <select value={regulationFilter} onChange={(e) => setRegulationFilter(e.target.value)}>
            <option value="">All</option>
            {regulations.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
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
        <div style={{ marginLeft: "auto", alignSelf: "center", color: "var(--text-muted)", fontSize: 12.5 }}>
          {filtered.length} of {rules.data?.length ?? 0} rules
        </div>
      </div>

      {rules.isLoading && <TableSkeleton columns={5} />}
      {rules.isError && <ErrorState message="Failed to load rules." />}
      {filtered.length === 0 && rules.data && (
        <EmptyState
          title="No matching rules"
          message="Try a different search term or clear the regulation/jurisdiction filters."
        />
      )}

      {filtered.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rule</th>
                <th>Condition</th>
                <th>Jurisdiction</th>
                <th>Version</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => {
                const version = versionLookup.data?.get(r.regulation_version_id);
                return (
                  <tr key={r.id} className="clickable" onClick={() => navigate(`/rules/${r.id}`)}>
                    <td>
                      <div>
                        <span className="mono text-accent" style={{ fontSize: 12 }}>
                          {r.rule_code}
                        </span>
                      </div>
                      <div style={{ marginTop: 2 }}>{r.title}</div>
                    </td>
                    <td>
                      <span className="mono text-secondary" style={{ fontSize: 12 }}>
                        {previewCondition(r.conditions) || "—"}
                      </span>
                    </td>
                    <td>
                      <NeutralBadge>{r.jurisdiction}</NeutralBadge>
                    </td>
                    <td className="mono text-secondary" style={{ fontSize: 12.5 }}>
                      {version ? `${version.regulation_name} ${version.version}` : "—"}
                    </td>
                    <td className="text-muted mono">{r.source_reference}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="card card-accent-line" style={{ marginTop: 24, paddingLeft: 22 }}>
        <div className="flex-between">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <FlaskConical size={16} className="text-accent" />
            <div>
              <strong>Engine evaluation</strong>
              <div className="text-secondary" style={{ fontSize: 12.5, marginTop: 2 }}>
                Run the deterministic regression suite against these rules.
              </div>
            </div>
          </div>
          <Link className="btn btn-secondary" to="/evaluation">
            Open Evaluation
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </div>
  );
}
