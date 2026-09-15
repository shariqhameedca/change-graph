from datetime import date

from app.engine.applicability import rule_is_applicable


def _rule(jurisdiction="ANY", effective_from=date(2023, 1, 1), effective_to=None):
    return {"jurisdiction": jurisdiction, "effective_from": effective_from, "effective_to": effective_to}


def test_any_jurisdiction_matches_everything():
    applicable, _ = rule_is_applicable(_rule(jurisdiction="ANY"), {"jurisdiction": "California"})
    assert applicable is True


def test_specific_jurisdiction_must_match():
    rule = _rule(jurisdiction="California")
    applicable, reason = rule_is_applicable(rule, {"jurisdiction": "New York"})
    assert applicable is False
    assert "jurisdiction" in reason.lower()

    applicable, _ = rule_is_applicable(rule, {"jurisdiction": "California"})
    assert applicable is True


def test_jurisdiction_match_is_case_insensitive():
    rule = _rule(jurisdiction="california")
    applicable, _ = rule_is_applicable(rule, {"jurisdiction": "California"})
    assert applicable is True


def test_effective_window_excludes_before_start():
    rule = _rule(effective_from=date(2024, 7, 1))
    applicable, reason = rule_is_applicable(rule, {"jurisdiction": "ANY"}, as_of=date(2024, 1, 1))
    assert applicable is False
    assert "effective" in reason.lower()


def test_effective_window_excludes_after_end():
    rule = _rule(effective_from=date(2020, 1, 1), effective_to=date(2021, 12, 31))
    applicable, _ = rule_is_applicable(rule, {"jurisdiction": "ANY"}, as_of=date(2023, 1, 1))
    assert applicable is False


def test_effective_window_includes_open_ended():
    rule = _rule(effective_from=date(2020, 1, 1), effective_to=None)
    applicable, _ = rule_is_applicable(rule, {"jurisdiction": "ANY"}, as_of=date(2030, 1, 1))
    assert applicable is True
