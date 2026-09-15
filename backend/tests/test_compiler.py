import asyncio

from app.compiler.llm_provider import MockLLMProvider
from app.compiler.regulation_parser import split_sections
from app.compiler.validator import validate_extraction

SAMPLE_TEXT = """
=== DEFINITION: Covered Borrower ===
A natural person borrower whose gross annual income is at least $50,000.
<<SOURCE: §2.2>>

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

=== EXCEPTION: RULE-017 ===
Military borrowers are exempt.
<<CONDITIONS: {"field": "borrower.military", "operator": "is_true", "value": true}>>
<<SOURCE: §4.2(a)>>
"""


def test_split_sections_finds_all_provisions():
    sections = split_sections(SAMPLE_TEXT)
    kinds = [s.kind for s in sections]
    assert kinds == ["DEFINITION", "RULE", "EXCEPTION"]


def test_split_sections_extracts_tags_and_strips_them_from_prose():
    sections = split_sections(SAMPLE_TEXT)
    rule_section = sections[1]
    assert rule_section.tags["JURISDICTION"] == "ANY"
    assert rule_section.tags["PRIORITY"] == "20"
    assert "<<" not in rule_section.body


def test_mock_provider_produces_valid_extraction():
    provider = MockLLMProvider()
    raw = asyncio.run(provider.generate_structured(SAMPLE_TEXT, "United States"))
    extraction = validate_extraction(raw)

    assert extraction.warnings == []
    assert len(extraction.rules) == 1
    assert extraction.rules[0].rule_code == "RULE-017"
    assert len(extraction.definitions) == 1
    assert len(extraction.exceptions) == 1


def test_validator_rejects_unknown_operator():
    raw = {
        "rules": [
            {
                "rule_code": "RULE-BAD",
                "title": "Bad rule",
                "effective_from": "2023-01-01",
                "conditions": {"field": "loan.apr", "operator": "not_a_real_operator", "value": 1},
                "actions": {"verdict": "FAIL", "action": "REJECT", "message": "x"},
            }
        ],
        "definitions": [],
        "exceptions": [],
    }
    extraction = validate_extraction(raw)
    assert len(extraction.rules) == 0
    assert any("unknown operator" in w.lower() for w in extraction.warnings)


def test_validator_drops_malformed_condition_but_keeps_others():
    raw = {
        "rules": [
            {
                "rule_code": "RULE-GOOD",
                "title": "Good rule",
                "effective_from": "2023-01-01",
                "conditions": {"field": "loan.apr", "operator": "greater_than", "value": 18},
                "actions": {"verdict": "FAIL", "action": "REJECT", "message": "x"},
            },
            {
                "rule_code": "RULE-MISSING-FIELD",
                "title": "Broken rule",
                "effective_from": "2023-01-01",
                "conditions": {"operator": "greater_than", "value": 18},
                "actions": {"verdict": "FAIL", "action": "REJECT", "message": "x"},
            },
        ],
        "definitions": [],
        "exceptions": [],
    }
    extraction = validate_extraction(raw)
    assert len(extraction.rules) == 1
    assert extraction.rules[0].rule_code == "RULE-GOOD"
    assert len(extraction.warnings) == 1
