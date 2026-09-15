"""The synthetic demo regulation: 'Consumer Lending Fairness Regulation'.

This is a fictional regulation written for demonstration purposes only.
It is not legal advice and does not describe any real law.

Content here is expressed as plain data (definitions/rules/exceptions) and
then rendered into tagged prose via `render_source_text`, which is exactly
the text format `app.compiler.regulation_parser` and the mock LLM provider
know how to read. Seeding therefore exercises the *real* compiler pipeline
instead of writing rows to the database directly.
"""

from __future__ import annotations

import copy
import json
from datetime import date
from typing import Any

DISCLAIMER = (
    "Synthetic demonstration regulation. Not legal advice. This text and all "
    "of its provisions are fictional and were written for the ChangeGraph "
    "proof of concept."
)

V1_EFFECTIVE_FROM = date(2023, 1, 1)
V1_EFFECTIVE_TO = date(2024, 6, 30)
V2_EFFECTIVE_FROM = date(2024, 7, 1)

DEFINITIONS: list[dict[str, Any]] = [
    {
        "term": "Covered Institution",
        "definition": (
            "An institution meeting conditions A, B and C: (A) it extends consumer "
            "credit in the ordinary course of business, (B) it is organized under "
            "the laws of a United States jurisdiction, and (C) it originates more "
            "than 100 consumer loans per year."
        ),
        "source_reference": "§2.1",
    },
    {
        "term": "Covered Borrower",
        "definition_v1": (
            "A natural person borrower whose gross annual income is at least "
            "$50,000, evaluated under the ability-to-repay provisions of this Part."
        ),
        "definition_v2": (
            "A natural person borrower whose gross annual income is at least "
            "$40,000, evaluated under the ability-to-repay provisions of this Part."
        ),
        "source_reference": "§2.2",
    },
    {
        "term": "Consumer Loan",
        "definition": (
            "An extension of credit to a natural person primarily for personal, "
            "family, or household purposes, excluding open-end credit plans and "
            "commercial financing."
        ),
        "source_reference": "§2.3",
    },
    {
        "term": "Annual Percentage Rate",
        "definition": (
            "The cost of credit expressed as a yearly rate, calculated in "
            "accordance with the truth-in-lending implementing rules of this "
            "jurisdiction."
        ),
        "source_reference": "§2.4",
    },
    {
        "term": "Military Borrower",
        "definition": (
            "A borrower who is a covered member of the armed forces, or a "
            "dependent of such a member, as defined by the Military Lending Act "
            "alignment provisions of this Part."
        ),
        "source_reference": "§2.5",
    },
    {
        "term": "High-Cost Loan",
        "definition": (
            "A consumer loan whose annual percentage rate exceeds the threshold "
            "established for the applicable jurisdiction under Section 4 of this "
            "Part."
        ),
        "source_reference": "§2.6",
    },
    {
        "term": "Debt-to-Income Ratio",
        "definition": (
            "The ratio of a borrower's total monthly debt obligations, including "
            "the proposed loan payment, to the borrower's gross monthly income."
        ),
        "source_reference": "§2.7",
    },
    {
        "term": "Balloon Payment",
        "definition": (
            "A single scheduled payment on a loan that is more than twice the "
            "amount of the average of the loan's earlier scheduled payments."
        ),
        "source_reference": "§2.8",
    },
    {
        "term": "Elder Borrower",
        "definition": (
            "A borrower who has attained the age of 65 years as of the date of "
            "the loan application."
        ),
        "source_reference": "§2.9",
    },
    {
        "term": "Payday Loan",
        "definition": (
            "A short-term, small-dollar consumer loan typically due on the "
            "borrower's next payday, regardless of the product name under which "
            "it is marketed."
        ),
        "source_reference": "§2.10",
    },
]


def _rule(
    code: str,
    title: str,
    body: str,
    rule_type: str,
    priority: int,
    jurisdiction: str,
    conditions: dict,
    actions: dict,
    ref: str,
    effective_from: date = V1_EFFECTIVE_FROM,
    effective_to: date | None = None,
) -> dict[str, Any]:
    return {
        "rule_code": code,
        "title": title,
        "body": body,
        "rule_type": rule_type,
        "priority": priority,
        "jurisdiction": jurisdiction,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "conditions": conditions,
        "actions": actions,
        "source_reference": ref,
    }


def _base_rules(apr_threshold: float, income_threshold: float) -> list[dict[str, Any]]:
    return [
        _rule(
            "RULE-017",
            "Consumer Loan APR Threshold",
            (
                "A consumer loan is non-compliant when the annual percentage rate "
                f"charged to the borrower exceeds {apr_threshold:g}% per annum. "
                "This threshold does not apply to military borrowers, who are "
                "instead governed by the Military Borrower APR Cap."
            ),
            "THRESHOLD",
            20,
            "ANY",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"field": "loan.apr", "operator": "greater_than", "value": apr_threshold},
            ]},
            {"verdict": "FAIL", "action": "REJECT", "message": f"APR exceeds the {apr_threshold:g}% threshold permitted for consumer loans."},
            "§4.2",
        ),
        _rule(
            "RULE-042",
            "Military Borrower APR Cap",
            (
                "A consumer loan extended to a military borrower is non-compliant "
                "when its annual percentage rate exceeds 20% per annum."
            ),
            "THRESHOLD",
            25,
            "ANY",
            {"all": [
                {"field": "borrower.military", "operator": "is_true", "value": True},
                {"field": "loan.apr", "operator": "greater_than", "value": 20},
            ]},
            {"verdict": "FAIL", "action": "REJECT", "message": "APR exceeds the 20% threshold permitted for military borrowers."},
            "§4.3",
        ),
        _rule(
            "RULE-002",
            "Minimum Credit Score Standard",
            (
                "A consumer loan applicant with a credit score below 580 does not "
                "meet the minimum eligibility standard of this Part."
            ),
            "ELIGIBILITY",
            50,
            "ANY",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"field": "borrower.credit_score", "operator": "less_than", "value": 580},
            ]},
            {"verdict": "FAIL", "action": "REJECT", "message": "Borrower credit score is below the minimum eligibility threshold."},
            "§5.1",
        ),
        _rule(
            "RULE-003",
            "Maximum Loan Term",
            "A consumer or auto loan may not have a term exceeding 84 months.",
            "THRESHOLD",
            80,
            "ANY",
            {"all": [
                {"field": "loan.product_type", "operator": "in", "value": ["consumer_loan", "auto_loan"]},
                {"field": "loan.term_months", "operator": "greater_than", "value": 84},
            ]},
            {"verdict": "FAIL", "action": "REJECT", "message": "Loan term exceeds the maximum permitted duration."},
            "§5.2",
        ),
        _rule(
            "RULE-004",
            "Debt-to-Income Ceiling",
            (
                "A consumer loan whose debt-to-income ratio exceeds 0.43 requires "
                "manual underwriting review."
            ),
            "THRESHOLD",
            60,
            "ANY",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"field": "loan.debt_to_income_ratio", "operator": "greater_than", "value": 0.43},
            ]},
            {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Debt-to-income ratio exceeds the standard underwriting threshold."},
            "§5.3",
        ),
        _rule(
            "RULE-005",
            "Income Verification Requirement",
            (
                "A consumer loan applicant who does not meet the Covered Borrower "
                f"income threshold of ${income_threshold:,.0f} requires manual "
                "income verification before origination."
            ),
            "ELIGIBILITY",
            70,
            "ANY",
            {"all": [
                {"field": "borrower.type", "operator": "equals", "value": "consumer"},
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"field": "borrower.income", "operator": "less_than", "value": income_threshold},
            ]},
            {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Borrower does not meet the covered-borrower income threshold and requires manual income verification."},
            "§5.4",
        ),
        _rule(
            "RULE-006",
            "Payday Loan APR Prohibition",
            "A payday loan may not carry an annual percentage rate above 36%.",
            "PROHIBITION",
            40,
            "ANY",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "payday_loan"},
                {"field": "loan.apr", "operator": "greater_than", "value": 36},
            ]},
            {"verdict": "FAIL", "action": "REJECT", "message": "Payday loan APR exceeds the absolute statutory ceiling."},
            "§5.5",
        ),
        _rule(
            "RULE-007",
            "Prepayment Penalty Prohibition",
            "Consumer loans may not include a prepayment penalty of any kind.",
            "PROHIBITION",
            90,
            "ANY",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"field": "loan.has_prepayment_penalty", "operator": "is_true", "value": True},
            ]},
            {"verdict": "FAIL", "action": "REJECT", "message": "Consumer loans may not include a prepayment penalty."},
            "§5.6",
        ),
        _rule(
            "RULE-008",
            "Balloon Payment Restriction",
            (
                "A loan with a balloon payment and a term under five years is "
                "prohibited."
            ),
            "PROHIBITION",
            90,
            "ANY",
            {"all": [
                {"field": "loan.has_balloon_payment", "operator": "is_true", "value": True},
                {"field": "loan.term_months", "operator": "less_than", "value": 60},
            ]},
            {"verdict": "FAIL", "action": "REJECT", "message": "Balloon payment structures are prohibited on loans with a term under five years."},
            "§5.7",
        ),
        _rule(
            "RULE-009",
            "Origination Fee Cap",
            (
                "A consumer loan with an origination fee exceeding 5% of the loan "
                "amount requires disclosure review."
            ),
            "THRESHOLD",
            85,
            "ANY",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"field": "loan.origination_fee_pct", "operator": "greater_than", "value": 5},
            ]},
            {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Origination fee exceeds the standard threshold and requires disclosure review."},
            "§5.8",
        ),
        _rule(
            "RULE-010",
            "Elder Borrower Enhanced Disclosure",
            (
                "A loan to an elder borrower exceeding $20,000 requires an "
                "enhanced disclosure review."
            ),
            "DISCLOSURE",
            75,
            "ANY",
            {"all": [
                {"field": "borrower.age", "operator": "greater_than_or_equal", "value": 65},
                {"field": "loan.amount", "operator": "greater_than", "value": 20000},
            ]},
            {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Elder borrower disclosure review required for loans above the standard amount threshold."},
            "§5.9",
        ),
        _rule(
            "RULE-018",
            "Adjustable Rate Disclosure",
            (
                "An adjustable-rate consumer loan requires a rate-change "
                "disclosure review."
            ),
            "DISCLOSURE",
            95,
            "ANY",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"field": "loan.rate_type", "operator": "equals", "value": "adjustable"},
            ]},
            {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Adjustable-rate consumer loans require rate-change disclosure review."},
            "§5.10",
        ),
        _rule(
            "RULE-011",
            "New York High-Cost Loan Threshold",
            (
                "In New York, a consumer loan is non-compliant when its annual "
                "percentage rate exceeds 16% per annum."
            ),
            "THRESHOLD",
            30,
            "New York",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"field": "loan.apr", "operator": "greater_than", "value": 16},
            ]},
            {"verdict": "FAIL", "action": "REJECT", "message": "New York high-cost loan threshold exceeded."},
            "§6.1",
        ),
        _rule(
            "RULE-012",
            "California Enhanced Disclosure Trigger",
            (
                "In California, a consumer loan with an annual percentage rate "
                "above 10% triggers an enhanced disclosure review."
            ),
            "DISCLOSURE",
            65,
            "California",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"field": "loan.apr", "operator": "greater_than", "value": 10},
            ]},
            {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "California enhanced disclosure requirement triggered."},
            "§6.2",
        ),
        _rule(
            "RULE-013",
            "Texas Vulnerable Borrower Protection",
            (
                "In Texas, a consumer loan to a military borrower or a borrower "
                "under 21 years of age is non-compliant when its annual "
                "percentage rate exceeds 20%."
            ),
            "THRESHOLD",
            35,
            "Texas",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"any": [
                    {"field": "borrower.military", "operator": "is_true", "value": True},
                    {"field": "borrower.age", "operator": "less_than", "value": 21},
                ]},
                {"field": "loan.apr", "operator": "greater_than", "value": 20},
            ]},
            {"verdict": "FAIL", "action": "REJECT", "message": "Texas vulnerable-borrower APR ceiling exceeded."},
            "§6.3",
        ),
        _rule(
            "RULE-014",
            "Small Business Carve-Out Notice",
            (
                "A small-business extension of credit above $250,000 requires "
                "commercial underwriting review."
            ),
            "DISCLOSURE",
            100,
            "ANY",
            {"all": [
                {"field": "borrower.type", "operator": "equals", "value": "small_business"},
                {"field": "loan.amount", "operator": "greater_than", "value": 250000},
            ]},
            {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Large small-business extension of credit requires commercial underwriting review."},
            "§7.1",
        ),
        _rule(
            "RULE-019",
            "Florida Small-Dollar Loan Protection",
            (
                "In Florida, a small-dollar consumer loan under $2,000 is "
                "non-compliant when its annual percentage rate exceeds 28%."
            ),
            "THRESHOLD",
            45,
            "Florida",
            {"all": [
                {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
                {"field": "loan.amount", "operator": "less_than", "value": 2000},
                {"field": "loan.apr", "operator": "greater_than", "value": 28},
            ]},
            {"verdict": "FAIL", "action": "REJECT", "message": "Florida small-dollar consumer loan APR ceiling exceeded."},
            "§6.4",
        ),
    ]


RULE_015_FORBEARANCE = _rule(
    "RULE-015",
    "Temporary Forbearance Flexibility",
    (
        "A consumer loan more than 90 days past due qualifies for a temporary "
        "forbearance flexibility review."
    ),
    "REVIEW",
    99,
    "ANY",
    {"all": [
        {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
        {"field": "loan.days_past_due", "operator": "greater_than", "value": 90},
    ]},
    {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Loan qualifies for temporary forbearance flexibility review."},
    "§8.1",
    effective_from=date(2020, 3, 1),
)

RULE_016_ENHANCED_DISCLOSURE = _rule(
    "RULE-016",
    "Enhanced APR Disclosure",
    (
        "A consumer loan with an annual percentage rate above 14% requires "
        "enhanced disclosure under the revised review threshold introduced in "
        "this version."
    ),
    "DISCLOSURE",
    55,
    "ANY",
    {"all": [
        {"field": "loan.product_type", "operator": "equals", "value": "consumer_loan"},
        {"field": "loan.apr", "operator": "greater_than", "value": 14},
    ]},
    {"verdict": "REVIEW", "action": "FLAG_REVIEW", "message": "Enhanced disclosure required for loans above the revised APR review threshold."},
    "§5.11",
    effective_from=V2_EFFECTIVE_FROM,
)


def _base_exceptions() -> list[dict[str, Any]]:
    return [
        {
            "rule_code": "RULE-017",
            "description": (
                "Military borrowers are exempted from the general APR threshold "
                "and are instead governed by the Military Borrower APR Cap "
                "(RULE-042)."
            ),
            "conditions": {"any": [{"field": "borrower.military", "operator": "is_true", "value": True}]},
            "source_reference": "§4.2(a)",
        },
        {
            "rule_code": "RULE-006",
            "description": (
                "Tribal lending institutions operating under an approved lending "
                "compact are exempt from this Part's payday loan APR ceiling."
            ),
            "conditions": {"field": "borrower.tribal_lending_compact", "operator": "is_true", "value": True},
            "source_reference": "§5.5(a)",
        },
        {
            "rule_code": "RULE-004",
            "description": (
                "Borrowers enrolled in an approved debt management plan are "
                "exempt from the debt-to-income ceiling."
            ),
            "conditions": {"field": "borrower.debt_management_plan", "operator": "is_true", "value": True},
            "source_reference": "§5.3(a)",
        },
        {
            "rule_code": "RULE-009",
            "description": (
                "Loans originated through a state housing finance agency program "
                "are exempt from the origination fee cap."
            ),
            "conditions": {"field": "loan.program", "operator": "equals", "value": "state_hfa"},
            "source_reference": "§5.8(a)",
        },
        {
            "rule_code": "RULE-011",
            "description": (
                "State-chartered credit unions are exempt from the New York "
                "high-cost loan threshold."
            ),
            "conditions": {"field": "borrower.lender_type", "operator": "equals", "value": "credit_union"},
            "source_reference": "§6.1(a)",
        },
    ]


EXCEPTION_013_V1 = {
    "rule_code": "RULE-013",
    "description": (
        "Borrowers who have completed an approved financial counseling course "
        "prior to origination are exempt from the Texas vulnerable-borrower "
        "APR ceiling."
    ),
    "conditions": {"field": "borrower.completed_financial_counseling", "operator": "is_true", "value": True},
    "source_reference": "§6.3(a)",
}

EXCEPTION_013_V2 = {
    "rule_code": "RULE-013",
    "description": (
        "Borrowers who have completed an approved financial counseling course "
        "within the preceding 180 days are exempt from the Texas "
        "vulnerable-borrower APR ceiling."
    ),
    "conditions": {"all": [
        {"field": "borrower.completed_financial_counseling", "operator": "is_true", "value": True},
        {"field": "borrower.counseling_days_ago", "operator": "less_than_or_equal", "value": 180},
    ]},
    "source_reference": "§6.3(a)",
}


def build_v1_content() -> tuple[list[dict], list[dict], list[dict]]:
    definitions = []
    for d in DEFINITIONS:
        text = d.get("definition") or d["definition_v1"]
        definitions.append({"term": d["term"], "definition": text, "source_reference": d["source_reference"]})

    rules = _base_rules(apr_threshold=18, income_threshold=50000) + [copy.deepcopy(RULE_015_FORBEARANCE)]
    exceptions = _base_exceptions() + [copy.deepcopy(EXCEPTION_013_V1)]
    return definitions, rules, exceptions


def build_v2_content() -> tuple[list[dict], list[dict], list[dict]]:
    definitions = []
    for d in DEFINITIONS:
        text = d.get("definition") or d["definition_v2"]
        definitions.append({"term": d["term"], "definition": text, "source_reference": d["source_reference"]})

    rules = _base_rules(apr_threshold=16, income_threshold=40000) + [copy.deepcopy(RULE_016_ENHANCED_DISCLOSURE)]
    exceptions = _base_exceptions() + [copy.deepcopy(EXCEPTION_013_V2)]
    return definitions, rules, exceptions


def render_source_text(definitions: list[dict], rules: list[dict], exceptions: list[dict]) -> str:
    """Renders structured content into the tagged prose format the compiler
    (mock or real) reads. A real LLM provider would ignore the tags and read
    the prose directly."""

    parts: list[str] = [
        "CONSUMER LENDING FAIRNESS REGULATION",
        "",
        DISCLAIMER,
        "",
        "This Part establishes fairness, disclosure, and eligibility "
        "requirements applicable to consumer lending within the jurisdictions "
        "adopting it.",
        "",
    ]

    for d in definitions:
        parts.append(f"=== DEFINITION: {d['term']} ===")
        parts.append(d["definition"])
        parts.append(f"<<SOURCE: {d['source_reference']}>>")
        parts.append("")

    for r in rules:
        parts.append(f"=== RULE: {r['rule_code']} | {r['title']} ===")
        parts.append(r["body"])
        parts.append(f"<<TYPE: {r['rule_type']}>>")
        parts.append(f"<<PRIORITY: {r['priority']}>>")
        parts.append(f"<<JURISDICTION: {r['jurisdiction']}>>")
        parts.append(f"<<EFFECTIVE_FROM: {r['effective_from'].isoformat()}>>")
        parts.append(f"<<EFFECTIVE_TO: {r['effective_to'].isoformat() if r['effective_to'] else ''}>>")
        parts.append(f"<<CONDITIONS: {json.dumps(r['conditions'])}>>")
        parts.append(f"<<ACTIONS: {json.dumps(r['actions'])}>>")
        parts.append(f"<<SOURCE: {r['source_reference']}>>")
        parts.append("")

    for e in exceptions:
        parts.append(f"=== EXCEPTION: {e['rule_code']} ===")
        parts.append(e["description"])
        parts.append(f"<<CONDITIONS: {json.dumps(e['conditions'])}>>")
        parts.append(f"<<SOURCE: {e['source_reference']}>>")
        parts.append("")

    return "\n".join(parts)
