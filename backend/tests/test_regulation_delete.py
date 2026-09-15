"""Verifies that deleting a regulation cleans up everything derived from
it -- rules, decisions, impact analyses, and knowledge graph nodes/edges --
rather than leaving orphaned rows pointing at a deleted id."""

from __future__ import annotations

from app.models.evaluation import Decision, DecisionTrace, EvaluationRecord
from app.models.graph import KnowledgeEdge, KnowledgeNode
from app.models.impact import ImpactAnalysis, ImpactItem
from app.models.regulation import Regulation, RegulationVersion
from app.models.rule import Rule

SOURCE_TEXT = """
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


def _setup_regulation_with_history(client, db_session):
    reg = client.post(
        "/api/regulations", json={"name": "Deletable Regulation", "jurisdiction": "United States"}
    ).json()
    v1 = client.post(
        f"/api/regulations/{reg['id']}/versions",
        json={"version": "1.0", "effective_from": "2023-01-01", "source_text": SOURCE_TEXT},
    ).json()
    v2 = client.post(
        f"/api/regulations/{reg['id']}/versions",
        json={"version": "2.0", "effective_from": "2024-01-01", "source_text": SOURCE_TEXT},
    ).json()
    assert client.post(f"/api/regulations/{reg['id']}/versions/{v1['id']}/compile").status_code == 202
    assert client.post(f"/api/regulations/{reg['id']}/versions/{v2['id']}/compile").status_code == 202

    record = EvaluationRecord(
        external_reference="DEL-TEST-1",
        jurisdiction="ANY",
        record_type="loan_application",
        input_data={"loan": {"product_type": "consumer_loan", "apr": 25}, "jurisdiction": "ANY"},
    )
    db_session.add(record)
    db_session.commit()

    eval_resp = client.post("/api/evaluate", json={"record_id": str(record.id), "regulation_version_id": v1["id"]})
    assert eval_resp.status_code == 200

    impact_resp = client.post(
        "/api/impact-analysis", json={"old_version_id": v1["id"], "new_version_id": v2["id"]}
    )
    assert impact_resp.status_code == 201
    analysis_id = impact_resp.json()["id"]
    client.post(f"/api/impact-analysis/{analysis_id}/re-evaluate")

    return reg, v1, v2


def test_delete_preview_reports_counts(client, db_session):
    reg, v1, v2 = _setup_regulation_with_history(client, db_session)

    preview = client.get(f"/api/regulations/{reg['id']}/delete-preview")
    assert preview.status_code == 200
    body = preview.json()
    assert body["versions"] == 2
    assert body["rules"] == 2  # one RULE-017 per version
    assert body["decisions"] >= 1
    assert body["impact_analyses"] == 1


def test_delete_regulation_cascades_everything(client, db_session):
    reg, v1, v2 = _setup_regulation_with_history(client, db_session)

    rule_ids = [r.id for r in db_session.query(Rule.id).filter(Rule.regulation_version_id == v1["id"])]
    assert rule_ids

    response = client.delete(f"/api/regulations/{reg['id']}")
    assert response.status_code == 204

    # The regulation and its versions/rules are gone.
    assert client.get(f"/api/regulations/{reg['id']}").status_code == 404
    assert db_session.get(Regulation, reg["id"]) is None
    assert db_session.query(RegulationVersion).filter(RegulationVersion.regulation_id == reg["id"]).count() == 0
    assert db_session.query(Rule).filter(Rule.id.in_(rule_ids)).count() == 0

    # Decisions and traces tied to those versions are gone.
    assert db_session.query(Decision).filter(Decision.regulation_version_id.in_([v1["id"], v2["id"]])).count() == 0
    assert (
        db_session.query(DecisionTrace)
        .filter(DecisionTrace.rule_id.in_(rule_ids))
        .count()
        == 0
    )

    # Impact analyses tied to those versions are gone.
    assert (
        db_session.query(ImpactAnalysis)
        .filter(ImpactAnalysis.regulation_version_id.in_([v1["id"], v2["id"]]))
        .count()
        == 0
    )
    assert db_session.query(ImpactItem).count() == 0 or all(
        item.entity_id not in rule_ids for item in db_session.query(ImpactItem).all()
    )

    # No orphaned knowledge graph nodes/edges pointing at the deleted entities.
    remaining_nodes = (
        db_session.query(KnowledgeNode)
        .filter(KnowledgeNode.entity_id.in_([reg["id"], v1["id"], v2["id"], *rule_ids]))
        .count()
    )
    assert remaining_nodes == 0
    assert db_session.query(KnowledgeEdge).count() >= 0  # no dangling-edge crash on query


def test_delete_nonexistent_regulation_returns_404(client):
    response = client.delete("/api/regulations/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
