"""Pure comparison operators used by the deterministic rule engine.

No operator here executes arbitrary code. Every operator is a plain function
over already-parsed Python values (numbers, strings, bools, dates). Rule
conditions are JSON data, never code.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


class OperatorError(ValueError):
    """Raised when an operator cannot be evaluated (unknown operator, bad value)."""


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise OperatorError(f"Cannot interpret {value!r} as a date")


def _numeric(value: Any) -> float:
    if isinstance(value, bool):
        raise OperatorError(f"Cannot interpret boolean {value!r} as a number")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise OperatorError(f"Cannot interpret {value!r} as a number") from exc
    raise OperatorError(f"Cannot interpret {value!r} as a number")


def op_equals(actual: Any, expected: Any) -> bool:
    return actual == expected


def op_not_equals(actual: Any, expected: Any) -> bool:
    return actual != expected


def op_greater_than(actual: Any, expected: Any) -> bool:
    return _numeric(actual) > _numeric(expected)


def op_greater_than_or_equal(actual: Any, expected: Any) -> bool:
    return _numeric(actual) >= _numeric(expected)


def op_less_than(actual: Any, expected: Any) -> bool:
    return _numeric(actual) < _numeric(expected)


def op_less_than_or_equal(actual: Any, expected: Any) -> bool:
    return _numeric(actual) <= _numeric(expected)


def op_in(actual: Any, expected: Any) -> bool:
    if not isinstance(expected, (list, tuple, set)):
        raise OperatorError("'in' expects a list value")
    return actual in expected


def op_not_in(actual: Any, expected: Any) -> bool:
    return not op_in(actual, expected)


def op_contains(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    return expected in actual


def op_starts_with(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    return str(actual).startswith(str(expected))


def op_is_true(actual: Any, _expected: Any) -> bool:
    return actual is True


def op_is_false(actual: Any, _expected: Any) -> bool:
    return actual is False


def op_before(actual: Any, expected: Any) -> bool:
    return _to_date(actual) < _to_date(expected)


def op_after(actual: Any, expected: Any) -> bool:
    return _to_date(actual) > _to_date(expected)


def op_between(actual: Any, expected: Any) -> bool:
    if not isinstance(expected, (list, tuple)) or len(expected) != 2:
        raise OperatorError("'between' expects a two-element [low, high] value")
    low, high = expected
    a = _to_date(actual)
    return _to_date(low) <= a <= _to_date(high)


def op_days_since(actual: Any, expected: Any, *, reference_date: date) -> bool:
    """True when at least `expected` whole days have elapsed since `actual`."""

    elapsed = (reference_date - _to_date(actual)).days
    return elapsed >= _numeric(expected)


_SIMPLE_OPERATORS = {
    "equals": op_equals,
    "not_equals": op_not_equals,
    "greater_than": op_greater_than,
    "greater_than_or_equal": op_greater_than_or_equal,
    "less_than": op_less_than,
    "less_than_or_equal": op_less_than_or_equal,
    "in": op_in,
    "not_in": op_not_in,
    "contains": op_contains,
    "starts_with": op_starts_with,
    "is_true": op_is_true,
    "is_false": op_is_false,
    "before": op_before,
    "after": op_after,
    "between": op_between,
}

DATE_REFERENCE_OPERATORS = {"days_since"}

ALL_OPERATORS = set(_SIMPLE_OPERATORS) | DATE_REFERENCE_OPERATORS


def apply_operator(
    operator: str, actual: Any, expected: Any, *, reference_date: date | None = None
) -> bool:
    if operator == "days_since":
        return op_days_since(actual, expected, reference_date=reference_date or date.today())
    fn = _SIMPLE_OPERATORS.get(operator)
    if fn is None:
        raise OperatorError(f"Unknown operator: {operator}")
    return fn(actual, expected)
