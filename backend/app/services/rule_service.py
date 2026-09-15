"""Helpers for turning ORM Rule rows into the plain dicts the (DB-agnostic)
deterministic engine consumes."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.rule import Rule, RuleException


def rule_to_dict(rule: Rule, exceptions: list[RuleException]) -> dict[str, Any]:
    return {
        "id": rule.id,
        "rule_code": rule.rule_code,
        "title": rule.title,
        "description": rule.description,
        "rule_type": rule.rule_type,
        "priority": rule.priority,
        "jurisdiction": rule.jurisdiction,
        "effective_from": rule.effective_from,
        "effective_to": rule.effective_to,
        "conditions": rule.conditions,
        "actions": rule.actions,
        "source_reference": rule.source_reference,
        "source_text": rule.source_text,
        "confidence": rule.confidence,
        "exceptions": [
            {
                "id": exc.id,
                "description": exc.description,
                "conditions": exc.conditions,
                "source_reference": exc.source_reference,
                "source_text": exc.source_text,
            }
            for exc in exceptions
        ],
    }


def load_rules_for_version(db: Session, regulation_version_id) -> list[dict[str, Any]]:
    rules = db.query(Rule).filter(Rule.regulation_version_id == regulation_version_id).all()
    if not rules:
        return []
    exceptions = (
        db.query(RuleException)
        .filter(RuleException.rule_id.in_([r.id for r in rules]))
        .all()
    )
    by_rule: dict[Any, list[RuleException]] = {}
    for exc in exceptions:
        by_rule.setdefault(exc.rule_id, []).append(exc)
    return [rule_to_dict(r, by_rule.get(r.id, [])) for r in rules]
