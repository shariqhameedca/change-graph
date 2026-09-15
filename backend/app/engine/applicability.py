"""Determines whether a rule (or exception) applies to a record at all,
before its conditions are ever evaluated.
"""

from __future__ import annotations

from datetime import date
from typing import Any

ANY_JURISDICTION = "ANY"


def jurisdiction_matches(rule_jurisdiction: str, record_jurisdiction: str) -> bool:
    if rule_jurisdiction.upper() == ANY_JURISDICTION:
        return True
    return rule_jurisdiction.strip().lower() == (record_jurisdiction or "").strip().lower()


def within_effective_window(
    effective_from: date, effective_to: date | None, as_of: date
) -> bool:
    if as_of < effective_from:
        return False
    if effective_to is not None and as_of > effective_to:
        return False
    return True


def rule_is_applicable(
    rule: dict[str, Any],
    record: dict[str, Any],
    as_of: date | None = None,
) -> tuple[bool, str]:
    """Return (applicable, reason). `rule` and `record` are plain dicts."""

    as_of = as_of or date.today()

    if not jurisdiction_matches(rule["jurisdiction"], record.get("jurisdiction", "")):
        return False, (
            f"Rule jurisdiction '{rule['jurisdiction']}' does not match "
            f"record jurisdiction '{record.get('jurisdiction')}'"
        )

    if not within_effective_window(rule["effective_from"], rule.get("effective_to"), as_of):
        return False, f"Rule is not effective as of {as_of.isoformat()}"

    return True, "Rule is applicable"
