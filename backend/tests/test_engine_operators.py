from datetime import date

import pytest

from app.engine.operators import OperatorError, apply_operator


@pytest.mark.parametrize(
    "operator,actual,expected,result",
    [
        ("equals", "consumer", "consumer", True),
        ("equals", "consumer", "business", False),
        ("not_equals", "consumer", "business", True),
        ("greater_than", 19.5, 18, True),
        ("greater_than", 18, 18, False),
        ("greater_than_or_equal", 18, 18, True),
        ("less_than", 500, 580, True),
        ("less_than_or_equal", 580, 580, True),
        ("in", "California", ["California", "Texas"], True),
        ("not_in", "Nevada", ["California", "Texas"], True),
        ("contains", "hello world", "world", True),
        ("starts_with", "RULE-017", "RULE-", True),
        ("is_true", True, None, True),
        ("is_true", False, None, False),
        ("is_false", False, None, True),
    ],
)
def test_simple_operators(operator, actual, expected, result):
    assert apply_operator(operator, actual, expected) is result


def test_before_and_after():
    assert apply_operator("before", "2023-01-01", "2024-01-01") is True
    assert apply_operator("after", "2024-06-01", "2024-01-01") is True


def test_between():
    assert apply_operator("between", "2023-06-01", ["2023-01-01", "2023-12-31"]) is True
    assert apply_operator("between", "2024-01-01", ["2023-01-01", "2023-12-31"]) is False


def test_days_since():
    assert apply_operator("days_since", "2023-01-01", 30, reference_date=date(2023, 2, 1)) is True
    assert apply_operator("days_since", "2023-01-01", 60, reference_date=date(2023, 1, 15)) is False


def test_unknown_operator_raises():
    with pytest.raises(OperatorError):
        apply_operator("unknown_op", 1, 2)


def test_type_mismatch_raises_operator_error():
    with pytest.raises(OperatorError):
        apply_operator("greater_than", "not-a-number", 18)
