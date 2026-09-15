"""Exercises the /api/evaluation/run benchmark endpoint against a minimal
regulation version whose two rules are enough to satisfy every case in
app.evaluation.benchmark.BENCHMARK_CASES."""

SOURCE_TEXT = """
=== RULE: RULE-017 | Consumer Loan APR Threshold ===
A consumer loan is non-compliant when its APR exceeds 16%.
<<TYPE: THRESHOLD>>
<<PRIORITY: 20>>
<<JURISDICTION: ANY>>
<<EFFECTIVE_FROM: 2023-01-01>>
<<EFFECTIVE_TO: >>
<<CONDITIONS: {"all": [{"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"}, {"field": "loan.apr", "operator": "greater_than", "value": 16}]}>>
<<ACTIONS: {"verdict": "FAIL", "action": "REJECT", "message": "APR exceeds threshold."}>>
<<SOURCE: §4.2>>

=== RULE: RULE-016 | Enhanced APR Disclosure ===
A consumer loan with an APR above 14% requires enhanced disclosure.
<<TYPE: DISCLOSURE>>
<<PRIORITY: 55>>
<<JURISDICTION: ANY>>
<<EFFECTIVE_FROM: 2023-01-01>>
<<EFFECTIVE_TO: >>
<<CONDITIONS: {"all": [{"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"}, {"field": "loan.apr", "operator": "greater_than", "value": 14}]}>>
<<ACTIONS: {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Enhanced disclosure required."}>>
<<SOURCE: §5.11>>

=== RULE: RULE-005 | Income Verification Requirement ===
A consumer loan applicant earning less than $40,000 requires manual review.
<<TYPE: ELIGIBILITY>>
<<PRIORITY: 70>>
<<JURISDICTION: ANY>>
<<EFFECTIVE_FROM: 2023-01-01>>
<<EFFECTIVE_TO: >>
<<CONDITIONS: {"all": [{"field": "borrower.type", "operator": "equals", "value": "consumer"}, {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"}, {"field": "borrower.income", "operator": "less_than", "value": 40000}]}>>
<<ACTIONS: {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Income below threshold."}>>
<<SOURCE: §5.4>>

=== EXCEPTION: RULE-017 ===
Military borrowers are exempt from the general APR threshold.
<<CONDITIONS: {"field": "borrower.military", "operator": "is_true", "value": true}>>
<<SOURCE: §4.2(a)>>
"""


def test_benchmark_suite_passes_against_matching_ruleset(client):
    reg = client.post(
        "/api/regulations",
        json={"name": "Benchmark Regulation", "jurisdiction": "United States"},
    ).json()
    version = client.post(
        f"/api/regulations/{reg['id']}/versions",
        json={"version": "1.0", "effective_from": "2023-01-01", "status": "ACTIVE", "source_text": SOURCE_TEXT},
    ).json()
    compile_resp = client.post(f"/api/regulations/{reg['id']}/versions/{version['id']}/compile")
    assert compile_resp.status_code == 202

    run_resp = client.post("/api/evaluation/run", params={"regulation_version_id": version["id"]})
    assert run_resp.status_code == 200
    body = run_resp.json()
    assert body["total"] == body["passed"], body["cases"]
    assert body["accuracy"] == 1.0
