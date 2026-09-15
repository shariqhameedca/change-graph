import { useMemo, useState } from "react";
import { TransitionChip, VerdictBadge } from "../components/Badge";
import { ErrorState, Loading } from "../components/StateViews";
import { Play, Sparkles } from "../components/icons";
import { useRegulationVersions, useRegulations, useSimulate } from "../hooks/useApi";
import type { EvaluateResponse, Verdict } from "../types";

const JURISDICTIONS = ["California", "New York", "Texas", "Florida", "Illinois"];

export function SimulatorPage() {
  const regulations = useRegulations();
  const regulationId = regulations.data?.[0]?.id;
  const versions = useRegulationVersions(regulationId);
  const sortedVersions = useMemo(
    () => (versions.data ?? []).slice().sort((a, b) => a.created_at.localeCompare(b.created_at)),
    [versions.data]
  );
  const versionA = sortedVersions[0];
  const versionB = sortedVersions.at(-1);

  const [jurisdiction, setJurisdiction] = useState("California");
  const [borrowerType, setBorrowerType] = useState("consumer");
  const [income, setIncome] = useState(45000);
  const [loanAmount, setLoanAmount] = useState(15000);
  const [apr, setApr] = useState(17);
  const [military, setMilitary] = useState(false);
  const [productType, setProductType] = useState("consumer_loan");

  const [resultA, setResultA] = useState<EvaluateResponse | null>(null);
  const [resultB, setResultB] = useState<EvaluateResponse | null>(null);
  const simulate = useSimulate();

  function buildInputData() {
    return {
      borrower: {
        type: borrowerType,
        state: jurisdiction,
        income,
        military,
        age: 35,
        credit_score: 700,
        lender_type: "bank",
        tribal_lending_compact: false,
        debt_management_plan: false,
        completed_financial_counseling: false,
        counseling_days_ago: 0,
      },
      loan: {
        amount: loanAmount,
        apr,
        product_type: productType,
        term_months: 36,
        origination_fee_pct: 2,
        has_prepayment_penalty: false,
        has_balloon_payment: false,
        rate_type: "fixed",
        days_past_due: 0,
        debt_to_income_ratio: 0.3,
        program: "standard",
      },
    };
  }

  async function handleEvaluate() {
    if (!versionA || !versionB) return;
    const inputData = buildInputData();
    const [a, b] = await Promise.all([
      simulate.mutateAsync({ regulation_version_id: versionA.id, jurisdiction, input_data: inputData }),
      simulate.mutateAsync({ regulation_version_id: versionB.id, jurisdiction, input_data: inputData }),
    ]);
    setResultA(a);
    setResultB(b);
  }

  const changedRules = useMemo(() => {
    if (!resultA || !resultB) return [];
    const firedA = new Map(resultA.trace.filter((t) => t.evaluation_result === "MATCH").map((t) => [t.rule_code, t]));
    const firedB = new Map(resultB.trace.filter((t) => t.evaluation_result === "MATCH").map((t) => [t.rule_code, t]));
    const codes = new Set([...firedA.keys(), ...firedB.keys()]);
    return Array.from(codes)
      .filter((code) => firedA.has(code) !== firedB.has(code))
      .map((code) => ({
        code,
        title: (firedA.get(code) ?? firedB.get(code))!.title,
        newlyFired: !firedA.has(code) && firedB.has(code),
      }));
  }, [resultA, resultB]);

  const changed = resultA && resultB && resultA.verdict !== resultB.verdict;

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">Scenario Simulator</span>
        <h1>What happens if the rule changes?</h1>
        <p className="page-subtitle">
          Evaluate a hypothetical case against two regulation versions and see exactly why the
          outcome changed.
        </p>
      </div>

      {regulations.isLoading && <Loading />}
      {(!versionA || !versionB) && !versions.isLoading && (
        <ErrorState message="At least two compiled regulation versions are required for the simulator." />
      )}

      {versionA && versionB && (
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div className="card card-elevated" style={{ flex: "1 1 380px", minWidth: 320 }}>
            <div className="section-title" style={{ marginTop: 0 }}>
              Inputs
            </div>
            <div className="form-grid">
              <div className="field">
                <label>Jurisdiction</label>
                <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)}>
                  {JURISDICTIONS.map((j) => (
                    <option key={j} value={j}>
                      {j}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Borrower type</label>
                <select value={borrowerType} onChange={(e) => setBorrowerType(e.target.value)}>
                  <option value="consumer">Consumer</option>
                  <option value="small_business">Small business</option>
                </select>
              </div>
              <div className="field">
                <label>Income ($)</label>
                <input type="number" value={income} onChange={(e) => setIncome(Number(e.target.value))} />
              </div>
              <div className="field">
                <label>Loan amount ($)</label>
                <input type="number" value={loanAmount} onChange={(e) => setLoanAmount(Number(e.target.value))} />
              </div>
              <div className="field">
                <label>APR (%)</label>
                <input type="number" step="0.1" value={apr} onChange={(e) => setApr(Number(e.target.value))} />
              </div>
              <div className="field">
                <label>Product type</label>
                <select value={productType} onChange={(e) => setProductType(e.target.value)}>
                  <option value="consumer_loan">Consumer loan</option>
                  <option value="auto_loan">Auto loan</option>
                  <option value="payday_loan">Payday loan</option>
                </select>
              </div>
              <div className="field">
                <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <input type="checkbox" checked={military} onChange={(e) => setMilitary(e.target.checked)} />
                  Military borrower
                </label>
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleEvaluate} disabled={simulate.isPending}>
              <Play size={14} />
              {simulate.isPending ? "Evaluating..." : "Evaluate"}
            </button>
            {simulate.isError && <ErrorState message={(simulate.error as Error).message} />}
          </div>

          <div style={{ flex: "1 1 320px", minWidth: 300 }}>
            {resultA && resultB ? (
              <div key={`${resultA.verdict}-${resultB.verdict}`} className="page-enter">
                <div
                  className="card card-elevated"
                  style={{
                    marginBottom: 16,
                    textAlign: "center",
                    padding: "28px 20px",
                    boxShadow: changed ? "var(--accent-glow)" : undefined,
                  }}
                >
                  {changed ? (
                    <>
                      <div className="text-muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 12 }}>
                        Result changed
                      </div>
                      <TransitionChip from={resultA.verdict as Verdict} to={resultB.verdict as Verdict} />
                    </>
                  ) : (
                    <>
                      <div className="text-muted" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 12 }}>
                        Result
                      </div>
                      <VerdictBadge verdict={resultB.verdict} />
                    </>
                  )}
                  <div style={{ display: "flex", justifyContent: "center", gap: 32, marginTop: 20 }}>
                    <div>
                      <div className="mono text-muted" style={{ fontSize: 11 }}>
                        {versionA.version}
                      </div>
                      <div style={{ marginTop: 6 }}>
                        <VerdictBadge verdict={resultA.verdict} />
                      </div>
                    </div>
                    <div>
                      <div className="mono text-muted" style={{ fontSize: 11 }}>
                        {versionB.version}
                      </div>
                      <div style={{ marginTop: 6 }}>
                        <VerdictBadge verdict={resultB.verdict} />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="section-title" style={{ marginTop: 0 }}>
                  Why did the result change?
                </div>
                {changedRules.length === 0 ? (
                  <div className="state-block">No rule triggering changed between versions.</div>
                ) : (
                  changedRules.map((r) => (
                    <div className="card" key={r.code} style={{ borderLeft: `2px solid ${r.newlyFired ? "var(--danger)" : "var(--success)"}` }}>
                      <span className="mono text-accent">{r.code}</span> {r.title}
                      <div className="text-secondary" style={{ marginTop: 4, fontSize: 12.5 }}>
                        {r.newlyFired ? "Newly triggered under the new version." : "No longer triggered under the new version."}
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="state-block">
                <Sparkles size={22} className="state-block-icon" />
                Set your inputs and click Evaluate to compare outcomes across both versions.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
