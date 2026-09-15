"""Deterministic condition evaluator.

Conditions are plain JSON: comparison leaves and `all` / `any` / `not` groups.
Evaluation is pure: same condition tree + same data + same reference date
always yields the same result tree. No code is ever executed from rule data.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.engine.operators import ALL_OPERATORS, OperatorError, apply_operator


def get_field(data: dict[str, Any], path: str) -> Any:
    """Resolve a dotted path (e.g. 'loan.apr') against a nested dict."""

    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def evaluate_condition(
    condition: dict[str, Any], data: dict[str, Any], reference_date: date | None = None
) -> dict[str, Any]:
    """Recursively evaluate a condition tree and return an annotated result tree."""

    reference_date = reference_date or date.today()

    if "all" in condition:
        children = [
            evaluate_condition(c, data, reference_date) for c in condition["all"]
        ]
        return {"all": children, "result": all(c["result"] for c in children)}

    if "any" in condition:
        children = [
            evaluate_condition(c, data, reference_date) for c in condition["any"]
        ]
        return {"any": children, "result": any(c["result"] for c in children)}

    if "not" in condition:
        child = evaluate_condition(condition["not"], data, reference_date)
        return {"not": child, "result": not child["result"]}

    field = condition.get("field")
    operator = condition.get("operator")
    expected = condition.get("value")

    if field is None or operator is None:
        raise ValueError(f"Malformed condition leaf: {condition!r}")
    if operator not in ALL_OPERATORS:
        raise OperatorError(f"Unknown operator: {operator}")

    actual = get_field(data, field)

    try:
        result = apply_operator(operator, actual, expected, reference_date=reference_date)
    except OperatorError:
        # A field that is missing or of the wrong shape never matches.
        result = False

    return {
        "field": field,
        "operator": operator,
        "expected": expected,
        "actual": actual,
        "result": result,
    }
