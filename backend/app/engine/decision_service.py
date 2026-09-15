"""The deterministic decision core.

`evaluate_record` is a pure function: given the same list of rule dicts, the
same record dict, and the same reference date, it always returns the same
result. This is what makes ChangeGraph's decisions reproducible and
explainable -- there is no model call anywhere in this file.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.engine.applicability import rule_is_applicable
from app.engine.evaluator import evaluate_condition

SEVERITY = {"PASS": 0, "REVIEW": 1, "FAIL": 2}


def _default_action() -> dict[str, str]:
    return {"verdict": "FAIL", "action": "REJECT", "message": "Rule condition matched."}


def evaluate_rule(
    rule: dict[str, Any], record: dict[str, Any], as_of: date
) -> dict[str, Any]:
    """Evaluate a single rule (with its exceptions) against a record."""

    applicable, reason = rule_is_applicable(rule, record, as_of)

    base = {
        "rule_id": rule["id"],
        "rule_code": rule["rule_code"],
        "title": rule["title"],
        "priority": rule.get("priority", 100),
        "source_reference": rule.get("source_reference"),
        "source_text": rule.get("source_text"),
    }

    if not applicable:
        return {
            **base,
            "applicable": False,
            "applicability_reason": reason,
            "condition_result": None,
            "exception_matched": None,
            "fired": False,
            "evaluation_result": "NOT_APPLICABLE",
            "action": None,
            "explanation": reason,
        }

    condition_result = evaluate_condition(rule["conditions"], record, as_of)

    exception_matched: dict[str, Any] | None = None
    for exc in rule.get("exceptions", []):
        exc_result = evaluate_condition(exc["conditions"], record, as_of)
        if exc_result["result"]:
            exception_matched = {
                "id": exc["id"],
                "description": exc["description"],
                "source_reference": exc.get("source_reference"),
                "source_text": exc.get("source_text"),
                "condition_result": exc_result,
            }
            break

    if exception_matched is not None:
        return {
            **base,
            "applicable": True,
            "applicability_reason": reason,
            "condition_result": condition_result,
            "exception_matched": exception_matched,
            "fired": False,
            "evaluation_result": "EXCEPTED",
            "action": None,
            "explanation": (
                f"Rule matched but was excepted: {exception_matched['description']}"
            ),
        }

    if not condition_result["result"]:
        return {
            **base,
            "applicable": True,
            "applicability_reason": reason,
            "condition_result": condition_result,
            "exception_matched": None,
            "fired": False,
            "evaluation_result": "NOT_MATCH",
            "action": None,
            "explanation": "Rule conditions were not met.",
        }

    action = rule.get("actions") or _default_action()
    return {
        **base,
        "applicable": True,
        "applicability_reason": reason,
        "condition_result": condition_result,
        "exception_matched": None,
        "fired": True,
        "evaluation_result": "MATCH",
        "action": action,
        "explanation": action.get("message", "Rule condition matched."),
    }


def evaluate_record(
    rules: list[dict[str, Any]],
    record: dict[str, Any],
    as_of: date | None = None,
) -> dict[str, Any]:
    """Evaluate every rule against a record and produce an overall decision."""

    as_of = as_of or date.today()
    trace = [evaluate_rule(rule, record, as_of) for rule in rules]

    fired = [t for t in trace if t["fired"]]
    applicable = [t for t in trace if t["applicable"]]

    verdict = "PASS"
    for t in fired:
        candidate = t["action"].get("verdict", "FAIL")
        if SEVERITY.get(candidate, 2) > SEVERITY.get(verdict, 0):
            verdict = candidate

    if fired:
        summary = (
            f"{len(fired)} of {len(applicable)} applicable rule(s) triggered a "
            f"violation."
        )
    elif applicable:
        summary = f"No violations found among {len(applicable)} applicable rule(s)."
    else:
        summary = "No rules were applicable to this record."

    return {
        "verdict": verdict,
        "summary": summary,
        "rules_evaluated": len(rules),
        "rules_applicable": len(applicable),
        "rules_fired": len(fired),
        "trace": sorted(trace, key=lambda t: t["priority"]),
    }
