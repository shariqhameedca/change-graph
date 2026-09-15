from datetime import date

from app.models.regulation import Regulation, RegulationVersion
from app.models.rule import Rule
from app.services.conflict_service import analyze_conflicts


def _make_version(db_session) -> RegulationVersion:
    regulation = Regulation(name="Conflict Test Regulation", jurisdiction="United States")
    db_session.add(regulation)
    db_session.flush()
    version = RegulationVersion(
        regulation_id=regulation.id, version="1.0", effective_from=date(2023, 1, 1), status="ACTIVE", source_text=""
    )
    db_session.add(version)
    db_session.flush()
    return version


def test_detects_overlapping_thresholds(db_session):
    version = _make_version(db_session)
    db_session.add_all([
        Rule(
            regulation_version_id=version.id, rule_code="RULE-017", title="General APR cap",
            jurisdiction="ANY", effective_from=date(2023, 1, 1),
            conditions={"field": "loan.apr", "operator": "greater_than", "value": 18},
            actions={"verdict": "FAIL", "action": "REJECT", "message": "x"},
        ),
        Rule(
            regulation_version_id=version.id, rule_code="RULE-042", title="Military APR cap",
            jurisdiction="ANY", effective_from=date(2023, 1, 1),
            conditions={"field": "loan.apr", "operator": "greater_than", "value": 20},
            actions={"verdict": "FAIL", "action": "REJECT", "message": "x"},
        ),
    ])
    db_session.flush()

    findings = analyze_conflicts(db_session, version.id)
    overlaps = [f for f in findings if f["type"] == "OVERLAP"]
    assert len(overlaps) == 1
    assert "RULE-042 is less restrictive than RULE-017" in overlaps[0]["description"]


def test_detects_contradictory_identical_conditions(db_session):
    version = _make_version(db_session)
    shared_conditions = {"field": "loan.apr", "operator": "greater_than", "value": 18}
    db_session.add_all([
        Rule(
            regulation_version_id=version.id, rule_code="RULE-A", title="A",
            jurisdiction="ANY", effective_from=date(2023, 1, 1),
            conditions=shared_conditions, actions={"verdict": "FAIL", "action": "REJECT", "message": "x"},
        ),
        Rule(
            regulation_version_id=version.id, rule_code="RULE-B", title="B",
            jurisdiction="ANY", effective_from=date(2023, 1, 1),
            conditions=shared_conditions, actions={"verdict": "PASS", "action": "ALLOW", "message": "x"},
        ),
    ])
    db_session.flush()

    findings = analyze_conflicts(db_session, version.id)
    assert any(f["type"] == "CONTRADICTION" for f in findings)


def test_no_conflict_across_non_overlapping_jurisdictions(db_session):
    version = _make_version(db_session)
    db_session.add_all([
        Rule(
            regulation_version_id=version.id, rule_code="RULE-CA", title="California cap",
            jurisdiction="California", effective_from=date(2023, 1, 1),
            conditions={"field": "loan.apr", "operator": "greater_than", "value": 18},
            actions={"verdict": "FAIL", "action": "REJECT", "message": "x"},
        ),
        Rule(
            regulation_version_id=version.id, rule_code="RULE-NY", title="New York cap",
            jurisdiction="New York", effective_from=date(2023, 1, 1),
            conditions={"field": "loan.apr", "operator": "greater_than", "value": 20},
            actions={"verdict": "FAIL", "action": "REJECT", "message": "x"},
        ),
    ])
    db_session.flush()

    findings = analyze_conflicts(db_session, version.id)
    assert findings == []
