import { useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ErrorState, Loading } from "../components/StateViews";
import { ArrowRight, GitCompareArrows } from "../components/icons";
import { usePageCrumb } from "../contexts/PageMetaContext";
import {
  useCreateImpactAnalysis,
  useDefinitions,
  useRules,
  useVersion,
  useVersionExceptions,
} from "../hooks/useApi";
import type { Rule } from "../types";

interface RuleDiff {
  code: string;
  kind: "ADDED" | "REMOVED" | "MODIFIED";
  oldRule?: Rule;
  newRule?: Rule;
}

function diffRules(oldRules: Rule[], newRules: Rule[]): RuleDiff[] {
  const oldByCode = new Map(oldRules.map((r) => [r.rule_code, r]));
  const newByCode = new Map(newRules.map((r) => [r.rule_code, r]));
  const diffs: RuleDiff[] = [];

  for (const [code, oldRule] of oldByCode) {
    if (!newByCode.has(code)) diffs.push({ code, kind: "REMOVED", oldRule });
  }
  for (const [code, newRule] of newByCode) {
    const oldRule = oldByCode.get(code);
    if (!oldRule) {
      diffs.push({ code, kind: "ADDED", newRule });
    } else if (
      JSON.stringify(oldRule.conditions) !== JSON.stringify(newRule.conditions) ||
      JSON.stringify(oldRule.actions) !== JSON.stringify(newRule.actions) ||
      oldRule.jurisdiction !== newRule.jurisdiction
    ) {
      diffs.push({ code, kind: "MODIFIED", oldRule, newRule });
    }
  }
  return diffs;
}

function flattenLeaves(node: unknown): { field: string; value: unknown }[] {
  if (!node || typeof node !== "object") return [];
  const obj = node as Record<string, unknown>;
  if (typeof obj.field === "string" && "value" in obj) return [{ field: obj.field, value: obj.value }];
  const leaves: { field: string; value: unknown }[] = [];
  for (const key of ["all", "any"]) {
    if (Array.isArray(obj[key])) {
      for (const child of obj[key] as unknown[]) leaves.push(...flattenLeaves(child));
    }
  }
  if (obj.not) leaves.push(...flattenLeaves(obj.not));
  return leaves;
}

function extractChangedLeaf(
  oldRule: Rule | undefined,
  newRule: Rule | undefined
): { field: string; oldValue: unknown; newValue: unknown } | null {
  if (!oldRule || !newRule) return null;
  const oldLeaves = flattenLeaves(oldRule.conditions);
  const newLeaves = flattenLeaves(newRule.conditions);
  for (const newLeaf of newLeaves) {
    const oldLeaf = oldLeaves.find((l) => l.field === newLeaf.field);
    if (oldLeaf && JSON.stringify(oldLeaf.value) !== JSON.stringify(newLeaf.value)) {
      return { field: newLeaf.field, oldValue: oldLeaf.value, newValue: newLeaf.value };
    }
  }
  return null;
}

export function VersionComparePage() {
  const { id: regulationId } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const oldVersionId = params.get("old") ?? undefined;
  const newVersionId = params.get("new") ?? undefined;

  const oldVersion = useVersion(regulationId, oldVersionId);
  const newVersion = useVersion(regulationId, newVersionId);
  const oldRules = useRules(oldVersionId);
  const newRules = useRules(newVersionId);
  const oldDefs = useDefinitions(regulationId, oldVersionId);
  const newDefs = useDefinitions(regulationId, newVersionId);
  const oldExceptions = useVersionExceptions(regulationId, oldVersionId);
  const newExceptions = useVersionExceptions(regulationId, newVersionId);
  const createAnalysis = useCreateImpactAnalysis();

  usePageCrumb(oldVersion.data && newVersion.data ? `${oldVersion.data.version} -> ${newVersion.data.version}` : null);

  const ruleDiffs = useMemo(
    () => (oldRules.data && newRules.data ? diffRules(oldRules.data, newRules.data) : []),
    [oldRules.data, newRules.data]
  );

  const definitionDiffs = useMemo(() => {
    if (!oldDefs.data || !newDefs.data) return [];
    const oldByTerm = new Map(oldDefs.data.map((d) => [d.term, d]));
    return newDefs.data
      .filter((d) => oldByTerm.has(d.term) && oldByTerm.get(d.term)!.definition !== d.definition)
      .map((d) => ({ term: d.term, oldText: oldByTerm.get(d.term)!.definition, newText: d.definition }));
  }, [oldDefs.data, newDefs.data]);

  if (!oldVersionId || !newVersionId) {
    return <ErrorState message="Select two versions to compare from the regulation page." />;
  }
  if (oldVersion.isLoading || newVersion.isLoading || oldRules.isLoading || newRules.isLoading) {
    return <Loading label="Comparing versions..." />;
  }
  if (!oldVersion.data || !newVersion.data) {
    return <ErrorState message="Failed to load versions." />;
  }

  const added = ruleDiffs.filter((d) => d.kind === "ADDED");
  const removed = ruleDiffs.filter((d) => d.kind === "REMOVED");
  const modified = ruleDiffs.filter((d) => d.kind === "MODIFIED");
  const exceptionDelta = (newExceptions.data?.length ?? 0) - (oldExceptions.data?.length ?? 0);
  const totalChanges = added.length + removed.length + modified.length + definitionDiffs.length + Math.abs(exceptionDelta);

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">Regulatory Change</span>
        <h1>Compare Regulation Versions</h1>
      </div>

      <div className="card card-elevated" style={{ marginBottom: 28, padding: "28px 32px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 36, flexWrap: "wrap" }}>
          <div style={{ textAlign: "center" }}>
            <div className="mono" style={{ fontSize: 26, fontWeight: 700, color: "var(--text-secondary)" }}>
              {oldVersion.data.version}
            </div>
            <div className="text-muted" style={{ fontSize: 12.5, marginTop: 4 }}>
              {oldVersion.data.effective_from}
            </div>
          </div>
          <ArrowRight size={22} className="text-accent" />
          <div style={{ textAlign: "center" }}>
            <div className="mono" style={{ fontSize: 26, fontWeight: 700, color: "var(--accent)" }}>
              {newVersion.data.version}
            </div>
            <div className="text-muted" style={{ fontSize: 12.5, marginTop: 4 }}>
              {newVersion.data.effective_from}
            </div>
          </div>
          <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: 36, textAlign: "center" }}>
            <div style={{ fontSize: 32, fontWeight: 700 }}>{totalChanges}</div>
            <div className="text-muted" style={{ fontSize: 12 }}>
              changes detected
            </div>
          </div>
        </div>
      </div>

      <div className="section-title">Change Summary</div>
      <div className="table-wrap" style={{ marginBottom: 24 }}>
        <table>
          <tbody>
            <ChangeRow label="Definitions" count={definitionDiffs.length} noun="changed" tone="warning" />
            <ChangeRow label="Rules" count={modified.length} noun="modified" tone="warning" />
            <ChangeRow label="Rules" count={added.length} noun="added" tone="success" />
            <ChangeRow label="Rules" count={removed.length} noun="removed" tone="danger" />
            <ChangeRow
              label="Exceptions"
              count={Math.abs(exceptionDelta)}
              noun={exceptionDelta >= 0 ? "added" : "removed"}
              tone={exceptionDelta >= 0 ? "success" : "danger"}
            />
          </tbody>
        </table>
      </div>

      <button
        className="btn btn-primary"
        disabled={createAnalysis.isPending}
        onClick={() =>
          createAnalysis.mutate(
            { old_version_id: oldVersionId, new_version_id: newVersionId },
            { onSuccess: (analysis) => navigate(`/impact-analysis/${analysis.id}`) }
          )
        }
      >
        <GitCompareArrows size={14} />
        {createAnalysis.isPending ? "Running impact analysis..." : "Run Full Impact Analysis"}
      </button>
      {createAnalysis.isError && <ErrorState message={(createAnalysis.error as Error).message} />}

      <div className="section-title">Rules Added ({added.length})</div>
      {added.length === 0 ? (
        <p className="text-muted">None.</p>
      ) : (
        added.map((d) => (
          <div className="card" key={d.code} style={{ borderLeft: "2px solid var(--success)" }}>
            <span className="mono text-accent">{d.newRule?.rule_code}</span> {d.newRule?.title}
          </div>
        ))
      )}

      <div className="section-title">Rules Removed ({removed.length})</div>
      {removed.length === 0 ? (
        <p className="text-muted">None.</p>
      ) : (
        removed.map((d) => (
          <div className="card" key={d.code} style={{ borderLeft: "2px solid var(--danger)" }}>
            <span className="mono text-accent">{d.oldRule?.rule_code}</span> {d.oldRule?.title}
          </div>
        ))
      )}

      <div className="section-title">Rules Modified ({modified.length})</div>
      {modified.length === 0 ? (
        <p className="text-muted">None.</p>
      ) : (
        modified.map((d) => {
          const changed = extractChangedLeaf(d.oldRule, d.newRule);
          return (
            <div className="card" key={d.code} style={{ borderLeft: "2px solid var(--warning)" }}>
              <div>
                <span className="mono text-accent">{d.newRule?.rule_code}</span> {d.newRule?.title}
              </div>
              {changed && (
                <div style={{ marginTop: 10 }}>
                  <div className="text-muted mono" style={{ fontSize: 11.5 }}>
                    {changed.field}
                  </div>
                  <div className="diff-box">
                    <span className="diff-old">{String(changed.oldValue)}</span>
                    <span className="diff-arrow">&rarr;</span>
                    <span className="diff-new">{String(changed.newValue)}</span>
                  </div>
                </div>
              )}
              {!changed && d.oldRule && d.newRule && JSON.stringify(d.oldRule.jurisdiction) !== JSON.stringify(d.newRule.jurisdiction) && (
                <div style={{ marginTop: 10 }}>
                  <div className="text-muted mono" style={{ fontSize: 11.5 }}>
                    jurisdiction
                  </div>
                  <div className="diff-box">
                    <span className="diff-old">{d.oldRule.jurisdiction}</span>
                    <span className="diff-arrow">&rarr;</span>
                    <span className="diff-new">{d.newRule.jurisdiction}</span>
                  </div>
                </div>
              )}
            </div>
          );
        })
      )}

      {definitionDiffs.length > 0 && (
        <>
          <div className="section-title">Definitions Changed</div>
          {definitionDiffs.map((d) => (
            <div className="card" key={d.term} style={{ borderLeft: "2px solid var(--warning)" }}>
              <strong className="mono text-cyan">{d.term}</strong>
              <div style={{ marginTop: 8 }}>
                <div className="diff-old">{d.oldText}</div>
                <div className="diff-new" style={{ marginTop: 4 }}>
                  {d.newText}
                </div>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function ChangeRow({
  label,
  count,
  noun,
  tone,
}: {
  label: string;
  count: number;
  noun: string;
  tone: "success" | "warning" | "danger";
}) {
  const color = tone === "success" ? "var(--success)" : tone === "danger" ? "var(--danger)" : "var(--warning)";
  return (
    <tr>
      <td style={{ width: 160 }}>{label}</td>
      <td>
        <span style={{ color, fontWeight: 650 }}>
          {count} {noun}
        </span>
      </td>
    </tr>
  );
}
