"""End-to-end integration test driven entirely through the HTTP API:
regulation -> compile -> rules -> evaluation -> decision -> impact analysis
-> re-evaluation. Mirrors the real product workflow."""

from __future__ import annotations

V1_TEXT = """
=== RULE: RULE-017 | Consumer Loan APR Threshold ===
A consumer loan is non-compliant when its APR exceeds 18%.
<<TYPE: THRESHOLD>>
<<PRIORITY: 20>>
<<JURISDICTION: ANY>>
<<EFFECTIVE_FROM: 2023-01-01>>
<<EFFECTIVE_TO: >>
<<CONDITIONS: {"all": [{"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"}, {"field": "loan.apr", "operator": "greater_than", "value": 18}]}>>
<<ACTIONS: {"verdict": "FAIL", "action": "REJECT", "message": "APR exceeds threshold."}>>
<<SOURCE: §4.2>>
"""

V2_TEXT = """
=== RULE: RULE-017 | Consumer Loan APR Threshold ===
A consumer loan is non-compliant when its APR exceeds 16%.
<<TYPE: THRESHOLD>>
<<PRIORITY: 20>>
<<JURISDICTION: ANY>>
<<EFFECTIVE_FROM: 2024-07-01>>
<<EFFECTIVE_TO: >>
<<CONDITIONS: {"all": [{"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"}, {"field": "loan.apr", "operator": "greater_than", "value": 16}]}>>
<<ACTIONS: {"verdict": "FAIL", "action": "REJECT", "message": "APR exceeds threshold."}>>
<<SOURCE: §4.2>>
"""


def test_full_regulation_to_impact_flow(client):
    reg_resp = client.post(
        "/api/regulations",
        json={"name": "Test Lending Regulation", "jurisdiction": "United States", "description": "test"},
    )
    assert reg_resp.status_code == 201
    regulation_id = reg_resp.json()["id"]

    v1_resp = client.post(
        f"/api/regulations/{regulation_id}/versions",
        json={"version": "1.0", "effective_from": "2023-01-01", "source_text": V1_TEXT},
    )
    assert v1_resp.status_code == 201
    v1_id = v1_resp.json()["id"]

    v2_resp = client.post(
        f"/api/regulations/{regulation_id}/versions",
        json={"version": "2.0", "effective_from": "2024-07-01", "source_text": V2_TEXT},
    )
    v2_id = v2_resp.json()["id"]

    compile_v1 = client.post(f"/api/regulations/{regulation_id}/versions/{v1_id}/compile")
    assert compile_v1.status_code == 202
    assert compile_v1.json()["result"]["rules_created"] == 1

    compile_v2 = client.post(f"/api/regulations/{regulation_id}/versions/{v2_id}/compile")
    assert compile_v2.status_code == 202

    rules_resp = client.get("/api/rules", params={"regulation_version_id": v1_id})
    assert len(rules_resp.json()) == 1
    assert rules_resp.json()[0]["rule_code"] == "RULE-017"

    # A record with APR 17% -- compliant under v1 (18% threshold), not under v2 (16%).
    record_id = _seed_record(client, apr=17.0)

    eval_resp = client.post("/api/evaluate", json={"record_id": record_id, "regulation_version_id": v1_id})
    assert eval_resp.status_code == 200
    assert eval_resp.json()["verdict"] == "PASS"
    decision_id = eval_resp.json()["decision_id"]

    decision_detail = client.get(f"/api/decisions/{decision_id}")
    assert decision_detail.status_code == 200

    impact_resp = client.post(
        "/api/impact-analysis", json={"old_version_id": v1_id, "new_version_id": v2_id}
    )
    assert impact_resp.status_code == 201
    analysis = impact_resp.json()
    assert analysis["summary"]["rules_modified"] == 1
    assert analysis["summary"]["decisions_affected"] >= 1

    reeval_resp = client.post(f"/api/impact-analysis/{analysis['id']}/re-evaluate")
    assert reeval_resp.status_code == 200
    reeval = reeval_resp.json()
    assert reeval["summary"]["decisions_changed"] == 1

    changes_resp = client.get(f"/api/impact-analysis/{analysis['id']}/decisions")
    changes = changes_resp.json()
    assert len(changes) == 1
    assert changes[0]["old_verdict"] == "PASS"
    assert changes[0]["new_verdict"] == "FAIL"
    assert changes[0]["changed"] is True

    graph_resp = client.get(f"/api/graph/regulations/{regulation_id}")
    assert graph_resp.status_code == 200
    assert len(graph_resp.json()["nodes"]) > 0

    impact_graph_resp = client.get(f"/api/graph/impact/{analysis['id']}")
    assert impact_graph_resp.status_code == 200


def _seed_record(client, apr: float) -> str:
    # There's no public "create record" endpoint (records are synthetic
    # demo data), so we insert directly through the evaluate/simulate path's
    # underlying model via a small helper endpoint substitute: use the
    # database session shared with the app through dependency override.
    from app.database import get_db
    from app.main import app
    from app.models.evaluation import EvaluationRecord

    db = next(app.dependency_overrides[get_db]())
    record = EvaluationRecord(
        external_reference="TEST-0001",
        jurisdiction="California",
        record_type="loan_application",
        input_data={
            "borrower": {"type": "consumer", "state": "California", "income": 90000, "military": False},
            "loan": {"amount": 15000, "apr": apr, "product_type": "consumer_loan", "term_months": 36},
        },
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return str(record.id)
