import uuid
from datetime import date

from app.engine.decision_service import evaluate_record

APR_RULE = {
    "id": uuid.uuid4(),
    "rule_code": "RULE-017",
    "title": "Consumer Loan APR Threshold",
    "priority": 20,
    "jurisdiction": "ANY",
    "effective_from": date(2023, 1, 1),
    "effective_to": None,
    "conditions": {"all": [
        {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
        {"field": "loan.apr", "operator": "greater_than", "value": 18},
    ]},
    "actions": {"verdict": "FAIL", "action": "REJECT", "message": "APR exceeds threshold."},
    "source_reference": "§4.2",
    "source_text": "APR threshold text.",
    "exceptions": [
        {
            "id": uuid.uuid4(),
            "description": "Military borrowers are exempt.",
            "conditions": {"field": "borrower.military", "operator": "is_true", "value": True},
            "source_reference": "§4.2(a)",
            "source_text": None,
        }
    ],
}

REVIEW_RULE = {
    "id": uuid.uuid4(),
    "rule_code": "RULE-005",
    "title": "Income Verification",
    "priority": 70,
    "jurisdiction": "ANY",
    "effective_from": date(2023, 1, 1),
    "effective_to": None,
    "conditions": {"field": "borrower.income", "operator": "less_than", "value": 50000},
    "actions": {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Income below threshold."},
    "source_reference": "§5.4",
    "source_text": None,
    "exceptions": [],
}

CALIFORNIA_ONLY_RULE = {
    "id": uuid.uuid4(),
    "rule_code": "RULE-012",
    "title": "California Disclosure",
    "priority": 65,
    "jurisdiction": "California",
    "effective_from": date(2023, 1, 1),
    "effective_to": None,
    "conditions": {"field": "loan.apr", "operator": "greater_than", "value": 10},
    "actions": {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "CA disclosure required."},
    "source_reference": "§6.2",
    "source_text": None,
    "exceptions": [],
}


def test_rule_fires_and_fails():
    record = {"jurisdiction": "ANY", "loan": {"product_type": "consumer_loan", "apr": 19.5}, "borrower": {"income": 90000, "military": False}}
    result = evaluate_record([APR_RULE], record)
    assert result["verdict"] == "FAIL"
    assert result["rules_fired"] == 1
    assert result["trace"][0]["evaluation_result"] == "MATCH"


def test_rule_does_not_fire_below_threshold():
    record = {"jurisdiction": "ANY", "loan": {"product_type": "consumer_loan", "apr": 12}, "borrower": {"income": 90000, "military": False}}
    result = evaluate_record([APR_RULE], record)
    assert result["verdict"] == "PASS"
    assert result["rules_fired"] == 0


def test_exception_prevents_rule_from_firing():
    record = {"jurisdiction": "ANY", "loan": {"product_type": "consumer_loan", "apr": 25}, "borrower": {"income": 90000, "military": True}}
    result = evaluate_record([APR_RULE], record)
    assert result["verdict"] == "PASS"
    assert result["trace"][0]["evaluation_result"] == "EXCEPTED"


def test_jurisdiction_specific_rule_only_applies_in_its_jurisdiction():
    ca_record = {"jurisdiction": "California", "loan": {"product_type": "consumer_loan", "apr": 15}, "borrower": {"income": 90000}}
    ny_record = {"jurisdiction": "New York", "loan": {"product_type": "consumer_loan", "apr": 15}, "borrower": {"income": 90000}}

    ca_result = evaluate_record([CALIFORNIA_ONLY_RULE], ca_record)
    ny_result = evaluate_record([CALIFORNIA_ONLY_RULE], ny_record)

    assert ca_result["verdict"] == "REVIEW"
    assert ny_result["verdict"] == "PASS"
    assert ny_result["trace"][0]["evaluation_result"] == "NOT_APPLICABLE"


def test_worst_verdict_wins_when_multiple_rules_fire():
    record = {
        "jurisdiction": "ANY",
        "loan": {"product_type": "consumer_loan", "apr": 25},
        "borrower": {"income": 30000, "military": False},
    }
    result = evaluate_record([APR_RULE, REVIEW_RULE], record)
    assert result["verdict"] == "FAIL"  # FAIL outranks REVIEW even though both fired
    assert result["rules_fired"] == 2


def test_only_review_fires_yields_review_verdict():
    record = {
        "jurisdiction": "ANY",
        "loan": {"product_type": "consumer_loan", "apr": 5},
        "borrower": {"income": 30000, "military": False},
    }
    result = evaluate_record([APR_RULE, REVIEW_RULE], record)
    assert result["verdict"] == "REVIEW"


def test_determinism_across_repeated_evaluations():
    record = {
        "jurisdiction": "California",
        "loan": {"product_type": "consumer_loan", "apr": 19.5},
        "borrower": {"income": 30000, "military": False},
    }
    rules = [APR_RULE, REVIEW_RULE, CALIFORNIA_ONLY_RULE]
    results = [evaluate_record(rules, record, as_of=date(2023, 6, 1)) for _ in range(100)]

    first = results[0]
    for other in results[1:]:
        assert other["verdict"] == first["verdict"]
        assert other["trace"] == first["trace"]
