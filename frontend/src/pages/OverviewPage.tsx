import { Link } from "react-router-dom";
import { MetricCard } from "../components/MetricCard";
import { PipelineVisual } from "../components/PipelineVisual";
import { EmptyState, MetricSkeleton } from "../components/StateViews";
import {
  ArrowRight,
  CheckCircle2,
  FileStack,
  GitCompareArrows,
  ListChecks,
} from "../components/icons";
import { useDecisions, useImpactAnalyses, useRegulations, useRules } from "../hooks/useApi";

export function OverviewPage() {
  const regulations = useRegulations();
  const rules = useRules();
  const decisions = useDecisions();
  const impactAnalyses = useImpactAnalyses();

  const latestAnalysis = impactAnalyses.data?.[0];
  const isLoading = regulations.isLoading || rules.isLoading || decisions.isLoading || impactAnalyses.isLoading;

  return (
    <div>
      <div className="hero">
        <div className="hero-content">
          <span className="page-eyebrow">Regulatory Intelligence</span>
          <h1>Understand how regulatory change propagates.</h1>
          <p className="hero-subtitle">
            Turn regulatory text into executable knowledge, trace decisions to their sources, and
            model the downstream impact of change.
          </p>
          <div className="btn-row" style={{ marginTop: 28 }}>
            {latestAnalysis ? (
              <Link className="btn btn-primary" to={`/impact-analysis/${latestAnalysis.id}`}>
                Explore Demo
                <ArrowRight size={14} />
              </Link>
            ) : (
              <Link className="btn btn-primary" to="/impact-analysis">
                Explore Demo
                <ArrowRight size={14} />
              </Link>
            )}
            <Link className="btn btn-secondary" to="/regulations">
              View Regulations
            </Link>
          </div>
          <div className="disclaimer">Synthetic demonstration data. Not legal advice.</div>
        </div>
      </div>

      {isLoading ? (
        <MetricSkeleton />
      ) : (
        <div className="metric-grid">
          <MetricCard
            label="Regulations"
            value={regulations.data?.length ?? 0}
            icon={<FileStack size={13} />}
          />
          <MetricCard
            label="Executable Rules"
            value={rules.data?.length ?? 0}
            icon={<ListChecks size={13} />}
            glow="cyan"
          />
          <MetricCard
            label="Decisions Evaluated"
            value={decisions.data?.length ?? 0}
            icon={<CheckCircle2 size={13} />}
            glow="success"
          />
          <MetricCard
            label="Impacted by Latest Change"
            value={latestAnalysis?.summary.decisions_changed ?? 0}
            icon={<GitCompareArrows size={13} />}
            glow="accent"
          />
        </div>
      )}

      <div className="section-title">How Regulation Becomes Executable</div>
      <div className="card">
        <PipelineVisual />
      </div>

      <div className="section-title">Recent Regulatory Change</div>
      {impactAnalyses.isLoading ? (
        <MetricSkeleton count={1} />
      ) : !latestAnalysis ? (
        <EmptyState
          title="No impact analysis yet"
          message="Compare two regulation versions to discover downstream changes to rules, policies, workflows, and decisions."
          action={
            <Link className="btn btn-primary" to="/impact-analysis">
              Compare Versions
            </Link>
          }
        />
      ) : (
        <div className="card card-accent-line" style={{ paddingLeft: 22 }}>
          <div className="flex-between">
            <div>
              <strong>Consumer Lending Fairness Regulation</strong>
              <div className="text-secondary" style={{ marginTop: 6, fontSize: 13 }}>
                {latestAnalysis.summary.rules_modified +
                  latestAnalysis.summary.rules_added +
                  latestAnalysis.summary.rules_removed}{" "}
                rule(s) changed &middot; {latestAnalysis.summary.decisions_changed} decision(s)
                affected
              </div>
            </div>
            <Link className="btn btn-primary" to={`/impact-analysis/${latestAnalysis.id}`}>
              View Impact
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
