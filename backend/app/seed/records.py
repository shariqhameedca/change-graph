"""Generates the synthetic historical record set used to demonstrate impact
analysis. Uses a fixed RNG seed so the demo dataset is reproducible."""

from __future__ import annotations

import random
from typing import Any

JURISDICTIONS = {
    "California": "CA",
    "New York": "NY",
    "Texas": "TX",
    "Florida": "FL",
    "Illinois": "IL",
}

JURISDICTION_WEIGHTS = [0.25, 0.2, 0.2, 0.2, 0.15]


def _pick_product_type(rng: random.Random, borrower_type: str) -> str:
    if borrower_type == "small_business":
        return "commercial_loan"
    return rng.choices(
        ["consumer_loan", "auto_loan", "payday_loan"],
        weights=[0.75, 0.15, 0.10],
    )[0]


def _curated_boundary_records() -> list[dict[str, Any]]:
    """A handful of hand-placed records sitting right at the thresholds that
    change between v1 and v2. This guarantees the demo always shows a rich
    set of verdict transitions regardless of how the random draw lands --
    the *inputs* are curated, but every verdict is still computed by the
    deterministic engine, never hardcoded."""

    base_borrower = {
        "type": "consumer",
        "military": False,
        "age": 34,
        "credit_score": 690,
        "lender_type": "bank",
        "tribal_lending_compact": False,
        "debt_management_plan": False,
        "completed_financial_counseling": False,
        "counseling_days_ago": 0,
    }
    base_loan = {
        "product_type": "consumer_loan",
        "term_months": 36,
        "origination_fee_pct": 2.0,
        "has_prepayment_penalty": False,
        "has_balloon_payment": False,
        "rate_type": "fixed",
        "days_past_due": 0,
        "debt_to_income_ratio": 0.3,
        "program": "standard",
    }

    records: list[dict[str, Any]] = []

    # APR sits between the new (16%) and old (18%) thresholds: PASS -> FAIL.
    for i, (jurisdiction, apr) in enumerate(
        [("Illinois", 16.4), ("Illinois", 17.2), ("Texas", 17.8), ("Florida", 16.9), ("California", 17.5)]
    ):
        records.append({
            "external_reference": f"BND-APR-{i}",
            "jurisdiction": jurisdiction,
            "record_type": "loan_application",
            "input_data": {
                "borrower": {**base_borrower, "state": jurisdiction, "income": 70000},
                "loan": {**base_loan, "apr": apr, "amount": 18000},
            },
        })

    # Income sits between the new (40k) and old (50k) covered-borrower
    # threshold, with nothing else that would fail: REVIEW -> PASS.
    for i, (jurisdiction, income) in enumerate(
        [("Illinois", 42000), ("Texas", 44000), ("Florida", 41000), ("California", 46000)]
    ):
        records.append({
            "external_reference": f"BND-INCOME-{i}",
            "jurisdiction": jurisdiction,
            "record_type": "loan_application",
            "input_data": {
                "borrower": {**base_borrower, "state": jurisdiction, "income": income},
                "loan": {**base_loan, "apr": 8.5, "amount": 9000},
            },
        })

    # Past due > 90 days: only qualifies for the (v1-only) forbearance
    # review; the provision is repealed in v2, so REVIEW -> PASS.
    for i, jurisdiction in enumerate(["Illinois", "Texas", "Florida"]):
        records.append({
            "external_reference": f"BND-FORBEAR-{i}",
            "jurisdiction": jurisdiction,
            "record_type": "loan_application",
            "input_data": {
                "borrower": {**base_borrower, "state": jurisdiction, "income": 70000},
                "loan": {**base_loan, "apr": 9.0, "amount": 12000, "days_past_due": 120},
            },
        })

    return records


def generate_records(count: int = 150, seed: int = 42) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    records: list[dict[str, Any]] = []

    for i in range(count):
        jurisdiction = rng.choices(list(JURISDICTIONS), weights=JURISDICTION_WEIGHTS)[0]
        abbr = JURISDICTIONS[jurisdiction]
        borrower_type = "small_business" if rng.random() < 0.12 else "consumer"
        military = borrower_type == "consumer" and rng.random() < 0.12
        age = rng.randint(19, 82)
        income = (
            rng.randint(90000, 450000)
            if borrower_type == "small_business"
            else round(rng.triangular(18000, 130000, 45000), -2)
        )
        credit_score = rng.randint(500, 820)
        product_type = _pick_product_type(rng, borrower_type)

        if product_type == "payday_loan":
            apr = round(rng.triangular(20, 60, 34), 1)
            amount = round(rng.uniform(200, 2500), 2)
            term_months = rng.choice([1, 2, 3])
        elif product_type == "commercial_loan":
            apr = round(rng.triangular(6, 24, 12), 1)
            amount = round(rng.uniform(50000, 500000), 2)
            term_months = rng.choice([24, 36, 60, 84, 120])
        else:
            # Concentrate mass around the 14-20% band so the APR threshold
            # change (18% -> 16%) produces a realistic number of flips.
            apr = round(rng.triangular(4, 28, 17), 2)
            amount = round(rng.uniform(1500, 60000), 2)
            term_months = rng.choice([12, 24, 36, 48, 60, 72, 84, 96])

        record = {
            "external_reference": f"{abbr}-{1000 + i}",
            "jurisdiction": jurisdiction,
            "record_type": "loan_application",
            "input_data": {
                "borrower": {
                    "type": borrower_type,
                    "state": jurisdiction,
                    "income": income,
                    "military": military,
                    "age": age,
                    "credit_score": credit_score,
                    "lender_type": "credit_union" if rng.random() < 0.05 else "bank",
                    "tribal_lending_compact": rng.random() < 0.02,
                    "debt_management_plan": rng.random() < 0.05,
                    "completed_financial_counseling": rng.random() < 0.10,
                    "counseling_days_ago": rng.randint(0, 400),
                },
                "loan": {
                    "amount": amount,
                    "apr": apr,
                    "product_type": product_type,
                    "term_months": term_months,
                    "origination_fee_pct": round(rng.uniform(0, 8), 2),
                    "has_prepayment_penalty": rng.random() < 0.08,
                    "has_balloon_payment": rng.random() < 0.05,
                    "rate_type": "adjustable" if rng.random() < 0.15 else "fixed",
                    "days_past_due": rng.randint(0, 150) if rng.random() < 0.10 else 0,
                    "debt_to_income_ratio": round(rng.triangular(0.1, 0.65, 0.32), 3),
                    "program": "state_hfa" if rng.random() < 0.05 else "standard",
                },
            },
        }
        records.append(record)

    records.extend(_curated_boundary_records())
    return records
