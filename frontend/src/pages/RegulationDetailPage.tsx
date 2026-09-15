import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { NeutralBadge } from "../components/Badge";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { DocumentUploadField } from "../components/DocumentUploadField";
import { ProgressBar } from "../components/ProgressBar";
import { CardSkeleton, EmptyState, ErrorState, Loading, TableSkeleton } from "../components/StateViews";
import { ArrowRight, GitCompareArrows, GraphIcon, Play, Trash2 } from "../components/icons";
import { usePageCrumb } from "../contexts/PageMetaContext";
import { useQueryClient } from "@tanstack/react-query";
import {
  useCompileJob,
  useCompileVersion,
  useCreateImpactAnalysis,
  useCreateVersion,
  useDefinitions,
  useDeletePreview,
  useDeleteRegulation,
  useRegulation,
  useRegulationGraph,
  useRules,
  useVersionExceptions,
} from "../hooks/useApi";

const TERMINAL_JOB_STATUSES = ["SUCCEEDED", "FAILED", "COMPLETED_WITH_WARNINGS", "CANCELLED"];

const TABS = ["Overview", "Rules", "Definitions", "Exceptions", "Dependencies", "Source"] as const;

export function RegulationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const regulation = useRegulation(id);
  usePageCrumb(regulation.data?.name);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  const [showNewVersionForm, setShowNewVersionForm] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const versions = regulation.data?.versions ?? [];
  const activeVersion = useMemo(() => {
    if (selectedVersionId) return versions.find((v) => v.id === selectedVersionId);
    return versions.at(-1);
  }, [versions, selectedVersionId]);

  const definitions = useDefinitions(id, activeVersion?.id);
  const rules = useRules(activeVersion?.id);
  const exceptions = useVersionExceptions(id, activeVersion?.id);
  const graph = useRegulationGraph(id);
  const compile = useCompileVersion(id);
  const compileJob = useCompileJob(activeJobId ?? undefined);
  const createVersion = useCreateVersion(id);
  const createImpactAnalysis = useCreateImpactAnalysis();
  const deletePreview = useDeletePreview(showDeleteDialog ? id : undefined);
  const deleteRegulation = useDeleteRegulation();
  const isCompiling =
    compile.isPending || (!!compileJob.data && !TERMINAL_JOB_STATUSES.includes(compileJob.data.status));

  useEffect(() => {
    if (compileJob.data && TERMINAL_JOB_STATUSES.includes(compileJob.data.status)) {
      queryClient.invalidateQueries({ queryKey: ["regulation-versions", id] });
      queryClient.invalidateQueries({ queryKey: ["rules"] });
    }
    // Only re-run when the job transitions to a (new) terminal status, not on every poll tick.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [compileJob.data?.status, id]);

  if (regulation.isLoading) return <Loading label="Loading regulation..." />;
  if (regulation.isError || !regulation.data) return <ErrorState message="Failed to load regulation." />;

  const reg = regulation.data;
  const previousVersion = versions.length >= 2 ? versions[versions.length - 2] : undefined;

  function handleRunImpactAnalysis() {
    if (!previousVersion || !activeVersion) return;
    createImpactAnalysis.mutate(
      { old_version_id: previousVersion.id, new_version_id: activeVersion.id },
      { onSuccess: (a) => navigate(`/impact-analysis/${a.id}`) }
    );
  }

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">Regulation</span>
        <h1>{reg.name}</h1>
        <div className="tag-row" style={{ marginTop: 12, alignItems: "center" }}>
          <NeutralBadge>{reg.jurisdiction}</NeutralBadge>
          {activeVersion && (
            <>
              <span className="text-muted mono" style={{ fontSize: 12 }}>
                {activeVersion.version}
              </span>
              <span className="text-muted" style={{ fontSize: 12.5 }}>
                Effective {activeVersion.effective_from}
              </span>
            </>
          )}
        </div>
        {reg.description && <p className="page-subtitle">{reg.description}</p>}
      </div>

      <div className="btn-row" style={{ marginBottom: isCompiling ? 8 : 24 }}>
        <button
          className="btn btn-primary"
          disabled={!activeVersion || compile.isPending || isCompiling}
          onClick={() =>
            activeVersion &&
            compile.mutate(activeVersion.id, { onSuccess: (job) => setActiveJobId(job.id) })
          }
        >
          {isCompiling ? "Compiling..." : "Compile Selected Version"}
        </button>
        <button className="btn btn-secondary" onClick={() => setShowNewVersionForm((v) => !v)}>
          Create New Version
        </button>
        {previousVersion && activeVersion && (
          <>
            <button
              className="btn btn-secondary"
              onClick={() =>
                navigate(`/regulations/${id}/compare?old=${previousVersion.id}&new=${activeVersion.id}`)
              }
            >
              <GitCompareArrows size={14} />
              Compare Versions
            </button>
            <button className="btn btn-secondary" disabled={createImpactAnalysis.isPending} onClick={handleRunImpactAnalysis}>
              <Play size={14} />
              {createImpactAnalysis.isPending ? "Analyzing..." : "Run Impact Analysis"}
            </button>
          </>
        )}
        <Link className="btn btn-secondary" to="/graph">
          <GraphIcon size={14} />
          View Knowledge Graph
        </Link>
      </div>

      {isCompiling && (
        <div style={{ marginTop: -4, marginBottom: 20, maxWidth: 420 }}>
          <ProgressBar
            completed={compileJob.data?.chunks_completed ?? 0}
            total={compileJob.data?.chunks_total ?? 1}
            status={compileJob.data?.status ?? "QUEUED"}
            label={compileJob.data?.current_step ?? undefined}
          />
        </div>
      )}

      {compileJob.data && TERMINAL_JOB_STATUSES.includes(compileJob.data.status) && compileJob.data.result && (
        <div
          className="card"
          style={{
            marginBottom: 20,
            borderColor:
              compileJob.data.status === "FAILED" ? "var(--danger-border)" : "var(--success-border)",
          }}
        >
          Compilation complete: {compileJob.data.result.rules_created} rules,{" "}
          {compileJob.data.result.definitions_created} definitions,{" "}
          {compileJob.data.result.exceptions_created} exceptions,{" "}
          {compileJob.data.result.relationships_created} relationships created.
          {compileJob.data.result.warnings.length > 0 && (
            <div className="text-secondary" style={{ marginTop: 6, fontSize: 12.5 }}>
              {compileJob.data.result.warnings.length} warning(s):{" "}
              {compileJob.data.result.warnings.join("; ")}
            </div>
          )}
        </div>
      )}
      {compileJob.data?.status === "FAILED" && !compileJob.data.result && (
        <ErrorState message={compileJob.data.error_message ?? "Compilation failed."} />
      )}
      {compile.isError && <ErrorState message={(compile.error as Error).message} />}
      {createImpactAnalysis.isError && <ErrorState message={(createImpactAnalysis.error as Error).message} />}

      {showNewVersionForm && (
        <NewVersionForm
          onSubmit={(payload) => {
            createVersion.mutate(payload, { onSuccess: () => setShowNewVersionForm(false) });
          }}
          pending={createVersion.isPending}
        />
      )}

      <div className="section-title">Versions</div>
      <div className="tabs">
        {versions.map((v) => (
          <div
            key={v.id}
            className={`tab ${activeVersion?.id === v.id ? "active" : ""}`}
            onClick={() => setSelectedVersionId(v.id)}
          >
            {v.version} <span className="text-muted mono">({v.status})</span>
          </div>
        ))}
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <div key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t}
          </div>
        ))}
      </div>

      {tab === "Overview" && (
        <div className="metric-grid">
          <div className="metric-card">
            <div className="metric-label">Versions</div>
            <div className="metric-value">{versions.length}</div>
          </div>
          <div className="metric-card" style={{ ["--metric-glow" as string]: "var(--danger-soft)" }}>
            <div className="metric-label">Rules</div>
            <div className="metric-value">{rules.data?.length ?? "—"}</div>
          </div>
          <div className="metric-card" style={{ ["--metric-glow" as string]: "var(--cyan-soft)" }}>
            <div className="metric-label">Definitions</div>
            <div className="metric-value">{definitions.data?.length ?? "—"}</div>
          </div>
          <div className="metric-card" style={{ ["--metric-glow" as string]: "var(--warning-soft)" }}>
            <div className="metric-label">Exceptions</div>
            <div className="metric-value">{exceptions.data?.length ?? "—"}</div>
          </div>
        </div>
      )}

      {tab === "Definitions" && (
        <>
          {definitions.isLoading && <TableSkeleton columns={3} />}
          {definitions.data && definitions.data.length === 0 && <EmptyState message="No definitions." />}
          {definitions.data && definitions.data.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Term</th>
                    <th>Definition</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {definitions.data.map((d) => (
                    <tr key={d.id}>
                      <td className="mono text-cyan">{d.term}</td>
                      <td>{d.definition}</td>
                      <td className="text-muted mono">{d.source_reference}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {tab === "Rules" && (
        <>
          {rules.isLoading && <TableSkeleton columns={5} />}
          {rules.data && rules.data.length === 0 && (
            <EmptyState message="No rules. Try compiling this version." />
          )}
          {rules.data && rules.data.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>Type</th>
                    <th>Jurisdiction</th>
                    <th>Priority</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.data.map((r) => (
                    <tr key={r.id} className="clickable" onClick={() => navigate(`/rules/${r.id}`)}>
                      <td>
                        <span className="mono text-accent" style={{ fontSize: 12 }}>
                          {r.rule_code}
                        </span>{" "}
                        {r.title}
                      </td>
                      <td>
                        <NeutralBadge>{r.rule_type}</NeutralBadge>
                      </td>
                      <td>{r.jurisdiction}</td>
                      <td>{r.priority}</td>
                      <td className="text-muted mono">{r.source_reference}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {tab === "Exceptions" && (
        <>
          {exceptions.isLoading && <TableSkeleton columns={2} />}
          {exceptions.data && exceptions.data.length === 0 && <EmptyState message="No exceptions." />}
          {exceptions.data && exceptions.data.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Description</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {exceptions.data.map((e) => (
                    <tr key={e.id}>
                      <td>{e.description}</td>
                      <td className="text-muted mono">{e.source_reference}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {tab === "Dependencies" && (
        <>
          {graph.isLoading && <CardSkeleton />}
          {graph.data && (
            <div className="card">
              <p className="text-secondary" style={{ margin: 0 }}>
                {graph.data.nodes.length} connected nodes and {graph.data.edges.length} relationships
                across all versions, policies, and workflows.
              </p>
              <Link className="btn btn-secondary" to="/graph" style={{ marginTop: 14 }}>
                Open full Knowledge Graph
                <ArrowRight size={14} />
              </Link>
            </div>
          )}
        </>
      )}

      {tab === "Source" && activeVersion && (
        <div className="card">
          <div className="flex-between" style={{ marginBottom: 12 }}>
            <strong>Version {activeVersion.version} source text</strong>
            <span className="text-muted" style={{ fontSize: 12 }}>
              {activeVersion.source_text.length.toLocaleString()} characters
            </span>
          </div>
          <pre className="pre-block" style={{ maxHeight: 480, overflowY: "auto" }}>
            {activeVersion.source_text}
          </pre>
        </div>
      )}

      <div className="section-title">Danger Zone</div>
      <div className="card" style={{ borderColor: "var(--danger-border)" }}>
        <div className="flex-between">
          <div>
            <strong>Delete this regulation</strong>
            <div className="text-secondary" style={{ fontSize: 12.5, marginTop: 4 }}>
              Permanently removes all versions, rules, definitions, exceptions, historical
              decisions, and impact analyses derived from it. This cannot be undone.
            </div>
          </div>
          <button className="btn btn-danger" onClick={() => setShowDeleteDialog(true)}>
            <Trash2 size={14} />
            Delete Regulation
          </button>
        </div>
      </div>

      {showDeleteDialog && (
        <ConfirmDialog
          title={`Delete "${reg.name}"?`}
          pending={deleteRegulation.isPending}
          onCancel={() => setShowDeleteDialog(false)}
          onConfirm={() =>
            deleteRegulation.mutate(reg.id, {
              onSuccess: () => navigate("/regulations"),
            })
          }
        >
          {deletePreview.isLoading && <p>Checking what will be removed...</p>}
          {deletePreview.data && (
            <>
              <p style={{ marginTop: 0 }}>This will permanently delete:</p>
              <ul style={{ margin: "0 0 12px", paddingLeft: 18 }}>
                <li>{deletePreview.data.versions} version(s)</li>
                <li>{deletePreview.data.rules} rule(s)</li>
                <li>{deletePreview.data.decisions} historical decision(s)</li>
                <li>{deletePreview.data.impact_analyses} impact analysis/analyses</li>
              </ul>
              <p style={{ margin: 0, fontWeight: 600, color: "var(--text-primary)" }}>
                This action cannot be undone.
              </p>
            </>
          )}
          {deleteRegulation.isError && (
            <p style={{ color: "var(--danger)", marginTop: 12 }}>
              {(deleteRegulation.error as Error).message}
            </p>
          )}
        </ConfirmDialog>
      )}
    </div>
  );
}

function NewVersionForm({
  onSubmit,
  pending,
}: {
  onSubmit: (payload: { version: string; effective_from: string; source_text: string }) => void;
  pending: boolean;
}) {
  const [version, setVersion] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [sourceText, setSourceText] = useState("");

  return (
    <div className="card card-elevated" style={{ marginBottom: 20 }}>
      <div className="section-title" style={{ marginTop: 0 }}>
        New Regulation Version
      </div>
      <div className="form-grid">
        <div className="field">
          <label>Version label</label>
          <input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="3.0" />
        </div>
        <div className="field">
          <label>Effective from</label>
          <input
            type="date"
            value={effectiveFrom}
            onChange={(e) => setEffectiveFrom(e.target.value)}
          />
        </div>
      </div>
      <DocumentUploadField onExtracted={(text) => setSourceText(text)} />
      <div className="field">
        <label>Source text</label>
        <textarea
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          rows={8}
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 12,
          }}
        />
      </div>
      <button
        className="btn btn-primary"
        disabled={pending || !version || !effectiveFrom}
        onClick={() => onSubmit({ version, effective_from: effectiveFrom, source_text: sourceText })}
      >
        {pending ? "Creating..." : "Create Version"}
      </button>
    </div>
  );
}
