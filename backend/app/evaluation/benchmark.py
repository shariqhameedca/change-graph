"""A small benchmark suite for the deterministic engine.

Each case pins an input record and the verdict/rules the engine must
produce. This is not model evaluation (there is no model in this path) --
it is a regression suite for the deterministic engine itself, exposed
through the API and UI as "Engine Evaluation".
"""

from __future__ import annotations

from typing import Any

BENCHMARK_CASES: list[dict[str, Any]] = [
    {
        # Illinois carries no state-specific rule in the demo regulation, so
        # this case exercises only the nationwide (ANY jurisdiction) rules --
        # both the APR threshold and the enhanced-disclosure rule fire for
        # an APR this far above either line.
        "name": "APR above threshold fails",
        "jurisdiction": "Illinois",
        "input": {
            "borrower": {"type": "consumer", "state": "Illinois", "income": 60000, "military": False, "credit_score": 680},
            "loan": {"amount": 25000, "apr": 19.5, "product_type": "consumer_loan", "term_months": 48},
        },
        "expected_verdict": "FAIL",
        "expected_fired_rules": ["RULE-016", "RULE-017"],
    },
    {
        "name": "APR within threshold passes",
        "jurisdiction": "Illinois",
        "input": {
            "borrower": {"type": "consumer", "state": "Illinois", "income": 60000, "military": False, "credit_score": 700},
            "loan": {"amount": 15000, "apr": 8.0, "product_type": "consumer_loan", "term_months": 36},
        },
        "expected_verdict": "PASS",
        "expected_fired_rules": [],
    },
    {
        # The military exception correctly suppresses RULE-017/RULE-042, but
        # does not exempt the borrower from the unrelated, universal
        # enhanced-disclosure rule -- so REVIEW (not PASS) is the correct
        # deterministic outcome here.
        "name": "Military borrower exception applies",
        "jurisdiction": "Illinois",
        "input": {
            "borrower": {"type": "consumer", "state": "Illinois", "income": 60000, "military": True, "credit_score": 640},
            "loan": {"amount": 12000, "apr": 17.0, "product_type": "consumer_loan", "term_months": 24},
        },
        "expected_verdict": "REVIEW",
        "expected_fired_rules": ["RULE-016"],
    },
    {
        "name": "Low income consumer flagged for review",
        "jurisdiction": "New York",
        "input": {
            "borrower": {"type": "consumer", "state": "New York", "income": 25000, "military": False, "credit_score": 590},
            "loan": {"amount": 8000, "apr": 14.0, "product_type": "consumer_loan", "term_months": 24},
        },
        "expected_verdict": "REVIEW",
        "expected_fired_rules": ["RULE-005"],
    },
    {
        "name": "Business loan is out of scope",
        "jurisdiction": "Florida",
        "input": {
            "borrower": {"type": "small_business", "state": "Florida", "income": 200000, "military": False, "credit_score": 720},
            "loan": {"amount": 100000, "apr": 22.0, "product_type": "commercial_loan", "term_months": 60},
        },
        "expected_verdict": "PASS",
        "expected_fired_rules": [],
    },
]
