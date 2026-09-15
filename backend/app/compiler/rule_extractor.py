"""Turns parsed Sections into the raw extraction dict shape expected by
`app.compiler.validator.validate_extraction`.

This is the piece that stands in for "semantic understanding" in the mock
provider: it reads the bracketed tags a human analyst (or an LLM) attached
to each provision and turns them into structured fields.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from app.compiler.regulation_parser import Section


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _parse_json_tag(value: str | None, warnings: list[str], context: str) -> dict[str, Any]:
    if not value:
        warnings.append(f"{context}: missing structured tag")
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        warnings.append(f"{context}: invalid JSON ({exc})")
        return {}


def extract_from_sections(sections: list[Section]) -> dict[str, Any]:
    warnings: list[str] = []
    rules: list[dict[str, Any]] = []
    definitions: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []

    for section in sections:
        if section.kind == "DEFINITION":
            definitions.append(
                {
                    "term": section.identifier,
                    "definition": section.body,
                    "source_reference": section.tags.get("SOURCE"),
                    "source_text": section.body,
                }
            )

        elif section.kind == "RULE":
            code, _, title = section.identifier.partition("|")
            code = code.strip()
            title = title.strip() or code
            conditions = _parse_json_tag(
                section.tags.get("CONDITIONS"), warnings, f"RULE {code} conditions"
            )
            actions = _parse_json_tag(
                section.tags.get("ACTIONS"), warnings, f"RULE {code} actions"
            )
            effective_from = _parse_date(section.tags.get("EFFECTIVE_FROM"))
            rules.append(
                {
                    "rule_code": code,
                    "title": title,
                    "description": section.body,
                    "rule_type": section.tags.get("TYPE", "GENERAL"),
                    "priority": int(section.tags.get("PRIORITY", "100") or 100),
                    "jurisdiction": section.tags.get("JURISDICTION", "ANY"),
                    "effective_from": effective_from or date(2020, 1, 1),
                    "effective_to": _parse_date(section.tags.get("EFFECTIVE_TO")),
                    "conditions": conditions,
                    "actions": actions,
                    "source_reference": section.tags.get("SOURCE"),
                    "source_text": section.body,
                    "confidence": float(section.tags.get("CONFIDENCE", "0.92") or 0.92),
                }
            )

        elif section.kind == "EXCEPTION":
            rule_code = section.identifier.strip()
            conditions = _parse_json_tag(
                section.tags.get("CONDITIONS"), warnings, f"EXCEPTION {rule_code} conditions"
            )
            exceptions.append(
                {
                    "rule_code": rule_code,
                    "description": section.body,
                    "conditions": conditions,
                    "source_reference": section.tags.get("SOURCE"),
                    "source_text": section.body,
                }
            )

    return {
        "rules": rules,
        "definitions": definitions,
        "exceptions": exceptions,
        "warnings": warnings,
    }
