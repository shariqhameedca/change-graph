import { useEffect, useState } from "react";
import { AccentBadge, NeutralBadge } from "../components/Badge";
import { EmptyState, ErrorState } from "../components/StateViews";
import { CheckCircle2, FlaskConical, Play, RefreshCw } from "../components/icons";
import { useEvaluationSuite, useVersionLookup } from "../hooks/useApi";
import { usePageCrumb } from "../contexts/PageMetaContext";

export function EvaluationPage() {
  usePageCrumb("Evaluation");
  const suite = useEvaluationSuite();
  const versionLookup = useVersionLookup();
  const [versionId, setVersionId] = useState<string>("");

  useEffect(() => {
    suite.mutate(undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const versions = Array.from(versionLookup.data?.values() ?? []);

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">Engine Evaluation</span>
        <h1>Deterministic engine benchmark</h1>
        <p className="page-subtitle">
          A regression suite for the rule engine itself -- not a model evaluation. Every case pins
          an input record and the verdict the engine must produce; this proves the engine is
          correct and reproducible, independent of anything an LLM does.
        </p>
      </div>

      <div className="filter-bar">
        <div className="field">
          <label>Regulation version</label>
          <select value={versionId} onChange={(e) => setVersionId(e.target.value)}>
            <option value="">Latest active</option>
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.regulation_name} {v.version}
              </option>
            ))}
          </select>
        </div>
        <button
          className="btn btn-primary"
          disabled={suite.isPending}
          onClick={() => suite.mutate(versionId || undefined)}
        >
          {suite.isPending ? (
            <RefreshCw size={14} className="spin-icon" />
          ) : (
            <Play size={14} />
          )}
          Run Benchmark
        </button>
      </div>

      {suite.isError && <ErrorState message={(suite.error as Error).message} />}

      {suite.data && (
        <>
          <div className="metric-grid">
            <div className="metric-card" style={{ ["--metric-glow" as string]: "var(--accent-soft)" }}>
              <div className="metric-label">
                <FlaskConical size={13} />
                Total Cases
              </div>
              <div className="metric-value">{suite.data.total}</div>
            </div>
            <div className="metric-card" style={{ ["--metric-glow" as string]: "var(--success-soft)" }}>
              <div className="metric-label">Passed</div>
              <div className="metric-value" style={{ color: "var(--success)" }}>
                {suite.data.passed}
              </div>
            </div>
            <div className="metric-card" style={{ ["--metric-glow" as string]: "var(--danger-soft)" }}>
              <div className="metric-label">Failed</div>
              <div className="metric-value" style={{ color: suite.data.failed ? "var(--danger)" : undefined }}>
                {suite.data.failed}
              </div>
            </div>
            <div className="metric-card" style={{ ["--metric-glow" as string]: "var(--cyan-soft)" }}>
              <div className="metric-label">Accuracy</div>
              <div className="metric-value">
                {Math.round(suite.data.accuracy * 100)}
                <span className="metric-unit">%</span>
              </div>
            </div>
          </div>

          <div className="section-title">Test Cases</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Expected Verdict</th>
                  <th>Actual Verdict</th>
                  <th>Rules Expected</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {suite.data.cases.map((c) => (
                  <tr key={c.name}>
                    <td>{c.name}</td>
                    <td className="mono">{c.expected_verdict}</td>
                    <td className="mono">{c.actual_verdict}</td>
                    <td>
                      <div className="tag-row">
                        {c.expected_fired_rules.length === 0 ? (
                          <span className="text-muted">none</span>
                        ) : (
                          c.expected_fired_rules.map((r) => <NeutralBadge key={r}>{r}</NeutralBadge>)
                        )}
                      </div>
                    </td>
                    <td>
                      {c.passed ? (
                        <span className="badge badge-pass">
                          <CheckCircle2 size={11} />
                          Pass
                        </span>
                      ) : (
                        <span className="badge badge-fail">Fail</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!suite.data && !suite.isPending && !suite.isError && (
        <EmptyState
          title="No benchmark run yet"
          message="Run the benchmark to verify the deterministic engine against a fixed set of expected outcomes."
        />
      )}

      <div className="section-title">Architecture note</div>
      <div className="card">
        <p style={{ margin: 0, color: "var(--text-secondary)" }}>
          <AccentBadge>LLM</AccentBadge> compiles regulation text into structured rules once, offline.{" "}
          <AccentBadge>Engine</AccentBadge> evaluates every record deterministically, online, with no
          model in the decision path. This suite tests the engine only -- the same input always
          produces the same verdict.
        </p>
      </div>
    </div>
  );
}
