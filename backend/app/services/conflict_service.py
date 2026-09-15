"""Heuristic conflict detection between rules.

This is intentionally simple -- a POC demonstration of the idea, not a
general-purpose legal reasoning engine. It looks for rules that constrain
the same field with numeric thresholds, or that reach different verdicts
from identical conditions, within jurisdictions that could overlap.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.rule import Rule

# "ABOVE" operators mean the rule violates when the actual value is above the
# threshold (e.g. APR > 18) -- a *smaller* threshold is stricter.
# "BELOW" operators mean the rule violates when the actual value is below the
# threshold (e.g. credit_score < 580) -- a *larger* threshold is stricter.
ABOVE_VIOLATION_OPS = {"greater_than", "greater_than_or_equal"}
BELOW_VIOLATION_OPS = {"less_than", "less_than_or_equal"}


def _flatten_leaves(node: dict[str, Any]) -> list[dict[str, Any]]:
    if "all" in node:
        return [leaf for child in node["all"] for leaf in _flatten_leaves(child)]
    if "any" in node:
        return [leaf for child in node["any"] for leaf in _flatten_leaves(child)]
    if "not" in node:
        return _flatten_leaves(node["not"])
    if "field" in node:
        return [node]
    return []


def _jurisdictions_overlap(a: str, b: str) -> bool:
    return a.upper() == "ANY" or b.upper() == "ANY" or a.strip().lower() == b.strip().lower()


def analyze_conflicts(db: Session, regulation_version_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
    query = db.query(Rule)
    if regulation_version_id is not None:
        query = query.filter(Rule.regulation_version_id == regulation_version_id)
    rules = query.all()

    findings: list[dict[str, Any]] = []

    for i, rule_a in enumerate(rules):
        leaves_a = _flatten_leaves(rule_a.conditions)
        for rule_b in rules[i + 1 :]:
            if not _jurisdictions_overlap(rule_a.jurisdiction, rule_b.jurisdiction):
                continue

            if rule_a.conditions == rule_b.conditions and rule_a.rule_code != rule_b.rule_code:
                if rule_a.actions.get("verdict") != rule_b.actions.get("verdict"):
                    findings.append(
                        {
                            "type": "CONTRADICTION",
                            "rule_a": rule_a.rule_code,
                            "rule_b": rule_b.rule_code,
                            "description": (
                                f"{rule_a.rule_code} and {rule_b.rule_code} have identical "
                                f"conditions but reach different verdicts "
                                f"({rule_a.actions.get('verdict')} vs {rule_b.actions.get('verdict')})."
                            ),
                        }
                    )
                else:
                    findings.append(
                        {
                            "type": "DUPLICATE",
                            "rule_a": rule_a.rule_code,
                            "rule_b": rule_b.rule_code,
                            "description": (
                                f"{rule_a.rule_code} and {rule_b.rule_code} are functionally "
                                f"identical."
                            ),
                        }
                    )
                continue

            leaves_b = _flatten_leaves(rule_b.conditions)
            for leaf_a in leaves_a:
                for leaf_b in leaves_b:
                    if leaf_a["field"] != leaf_b["field"]:
                        continue
                    same_direction = (
                        leaf_a["operator"] in ABOVE_VIOLATION_OPS
                        and leaf_b["operator"] in ABOVE_VIOLATION_OPS
                    ) or (
                        leaf_a["operator"] in BELOW_VIOLATION_OPS
                        and leaf_b["operator"] in BELOW_VIOLATION_OPS
                    )
                    if not same_direction:
                        continue
                    try:
                        value_a, value_b = float(leaf_a["value"]), float(leaf_b["value"])
                    except (TypeError, ValueError):
                        continue
                    if value_a == value_b:
                        continue

                    if leaf_a["operator"] in ABOVE_VIOLATION_OPS:
                        a_is_stricter = value_a < value_b
                    else:
                        a_is_stricter = value_a > value_b
                    stricter, looser = (
                        (rule_a.rule_code, rule_b.rule_code)
                        if a_is_stricter
                        else (rule_b.rule_code, rule_a.rule_code)
                    )
                    findings.append(
                        {
                            "type": "OVERLAP",
                            "rule_a": rule_a.rule_code,
                            "rule_b": rule_b.rule_code,
                            "description": (
                                f"{rule_a.rule_code} and {rule_b.rule_code} both constrain "
                                f"'{leaf_a['field']}'. {looser} is less restrictive than "
                                f"{stricter} ({leaf_a['value']} vs {leaf_b['value']}). "
                                f"A precedence relationship may be required if their "
                                f"jurisdictions or exceptions overlap."
                            ),
                        }
                    )

    return findings
