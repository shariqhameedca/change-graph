import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { DocumentUploadField } from "../components/DocumentUploadField";
import { ProgressBar } from "../components/ProgressBar";
import { ErrorState } from "../components/StateViews";
import { Sparkles } from "../components/icons";
import { useCompileJob } from "../hooks/useApi";
import type { CompileJob, Regulation, RegulationVersion } from "../types";

const TODAY = new Date().toISOString().slice(0, 10);
const TERMINAL_JOB_STATUSES = ["SUCCEEDED", "FAILED", "COMPLETED_WITH_WARNINGS", "CANCELLED"];

export function NewRegulationPage() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [description, setDescription] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");

  const [version, setVersion] = useState("1.0");
  const [effectiveFrom, setEffectiveFrom] = useState(TODAY);
  const [sourceText, setSourceText] = useState("");
  const [compileImmediately, setCompileImmediately] = useState(true);

  const [step, setStep] = useState<"idle" | "creating-regulation" | "creating-version" | "compiling" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [pendingRegulationId, setPendingRegulationId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const compileJob = useCompileJob(jobId ?? undefined);

  const canSubmit = name.trim() && jurisdiction.trim() && sourceText.trim() && step === "idle";

  useEffect(() => {
    if (
      pendingRegulationId &&
      compileJob.data &&
      TERMINAL_JOB_STATUSES.includes(compileJob.data.status)
    ) {
      navigate(`/regulations/${pendingRegulationId}`);
    }
    // Only act when the job's status actually changes, not on every poll tick.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [compileJob.data?.status, pendingRegulationId]);

  async function handleSubmit() {
    setError(null);
    try {
      setStep("creating-regulation");
      const regulation = await api.post<Regulation>("/regulations", {
        name: name.trim(),
        jurisdiction: jurisdiction.trim(),
        description: description.trim() || null,
        source_url: sourceUrl.trim() || null,
      });

      setStep("creating-version");
      const createdVersion = await api.post<RegulationVersion>(`/regulations/${regulation.id}/versions`, {
        version: version.trim(),
        effective_from: effectiveFrom,
        source_text: sourceText,
      });

      if (compileImmediately) {
        setStep("compiling");
        const job = await api.post<CompileJob>(
          `/regulations/${regulation.id}/versions/${createdVersion.id}/compile`
        );
        setPendingRegulationId(regulation.id);
        setJobId(job.id);
        return; // the effect above navigates once the job reaches a terminal state
      }

      navigate(`/regulations/${regulation.id}`);
    } catch (err) {
      setStep("error");
      setError(err instanceof Error ? err.message : "Something went wrong.");
    }
  }

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">New Source</span>
        <h1>New Regulation</h1>
        <p className="page-subtitle">
          Bring your own regulatory text -- paste it or upload a document -- and ChangeGraph will
          compile it into executable rules.
        </p>
      </div>

      <div className="card card-elevated" style={{ maxWidth: 720 }}>
        <div className="section-title" style={{ marginTop: 0 }}>
          Regulation
        </div>
        <div className="form-grid">
          <div className="field">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Small Business Lending Disclosure Act" />
          </div>
          <div className="field">
            <label>Jurisdiction</label>
            <input value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} placeholder="e.g. Ohio, or United States" />
          </div>
        </div>
        <div className="field">
          <label>Description (optional)</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="field">
          <label>Source URL (optional)</label>
          <input value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} placeholder="Link to the official text, if public" />
        </div>

        <div className="section-title">First Version</div>
        <div className="form-grid">
          <div className="field">
            <label>Version label</label>
            <input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="1.0" />
          </div>
          <div className="field">
            <label>Effective from</label>
            <input type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} />
          </div>
        </div>

        <DocumentUploadField onExtracted={(text) => setSourceText(text)} />

        <div className="field">
          <label>Regulation text</label>
          <textarea
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            rows={14}
            placeholder="Paste the regulation's text here, or upload a document above."
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              padding: 10,
              border: "1px solid var(--border-strong)",
              borderRadius: 6,
            }}
          />
        </div>

        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, marginBottom: 14 }}>
          <input
            type="checkbox"
            checked={compileImmediately}
            onChange={(e) => setCompileImmediately(e.target.checked)}
          />
          Compile immediately after creating (recommended)
        </label>

        {error && <ErrorState message={error} />}

        <div className="btn-row" style={{ marginTop: 12 }}>
          <button className="btn btn-primary" disabled={!canSubmit} onClick={handleSubmit}>
            <Sparkles size={14} />
            {step === "idle" || step === "error" ? "Create Regulation" : STEP_LABELS[step]}
          </button>
        </div>
        {step === "compiling" && (
          <div style={{ marginTop: 12 }}>
            <ProgressBar
              completed={compileJob.data?.chunks_completed ?? 0}
              total={compileJob.data?.chunks_total ?? 1}
              status={compileJob.data?.status ?? "QUEUED"}
              label={compileJob.data?.current_step ?? undefined}
            />
          </div>
        )}
      </div>
    </div>
  );
}

const STEP_LABELS: Record<string, string> = {
  "creating-regulation": "Creating regulation...",
  "creating-version": "Saving version text...",
  compiling: "Compiling with the LLM...",
};
