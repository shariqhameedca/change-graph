"""Pydantic validation for LLM-extracted (or mock-extracted) regulation content.

Nothing reaches the database, or the deterministic engine, without passing
through here first.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.engine.operators import ALL_OPERATORS


class ExtractedRule(BaseModel):
    rule_code: str
    title: str
    description: str = ""
    rule_type: str = "GENERAL"
    priority: int = 100
    jurisdiction: str = "ANY"
    effective_from: date
    effective_to: date | None = None
    conditions: dict[str, Any]
    actions: dict[str, Any]
    source_reference: str | None = None
    source_text: str | None = None
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class ExtractedDefinition(BaseModel):
    term: str
    definition: str
    source_reference: str | None = None
    source_text: str | None = None


class ExtractedException(BaseModel):
    rule_code: str
    description: str
    conditions: dict[str, Any]
    source_reference: str | None = None
    source_text: str | None = None


class ExtractionResult(BaseModel):
    rules: list[ExtractedRule] = Field(default_factory=list)
    definitions: list[ExtractedDefinition] = Field(default_factory=list)
    exceptions: list[ExtractedException] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def validate_condition_tree(node: Any, path: str, warnings: list[str]) -> bool:
    """Recursively validate a condition tree. Appends human-readable warnings."""

    if not isinstance(node, dict):
        warnings.append(f"{path}: condition node must be an object")
        return False

    if "all" in node or "any" in node:
        key = "all" if "all" in node else "any"
        children = node[key]
        if not isinstance(children, list) or not children:
            warnings.append(f"{path}.{key}: must be a non-empty list")
            return False
        return all(
            validate_condition_tree(c, f"{path}.{key}[{i}]", warnings)
            for i, c in enumerate(children)
        )

    if "not" in node:
        return validate_condition_tree(node["not"], f"{path}.not", warnings)

    field_name = node.get("field")
    operator = node.get("operator")
    if not field_name or not isinstance(field_name, str):
        warnings.append(f"{path}: missing or invalid 'field'")
        return False
    if operator not in ALL_OPERATORS:
        warnings.append(f"{path}: unknown operator '{operator}'")
        return False
    if "value" not in node:
        warnings.append(f"{path}: missing 'value'")
        return False
    return True


def validate_extraction(raw: dict[str, Any]) -> ExtractionResult:
    """Parse and validate raw extraction output, dropping invalid entries.

    Invalid rules/definitions/exceptions are skipped (not fatal) and recorded
    as warnings in the compilation report -- this mirrors how a real
    extraction pipeline must tolerate imperfect LLM output.
    """

    warnings: list[str] = list(raw.get("warnings", []))

    rules: list[ExtractedRule] = []
    for i, item in enumerate(raw.get("rules", [])):
        cond_warnings: list[str] = []
        if not validate_condition_tree(item.get("conditions", {}), f"rules[{i}].conditions", cond_warnings):
            warnings.extend(cond_warnings)
            continue
        try:
            rules.append(ExtractedRule.model_validate(item))
        except Exception as exc:  # noqa: BLE001 - collected as a warning, not raised
            warnings.append(f"rules[{i}]: {exc}")

    definitions: list[ExtractedDefinition] = []
    for i, item in enumerate(raw.get("definitions", [])):
        try:
            definitions.append(ExtractedDefinition.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"definitions[{i}]: {exc}")

    exceptions: list[ExtractedException] = []
    for i, item in enumerate(raw.get("exceptions", [])):
        cond_warnings = []
        if not validate_condition_tree(item.get("conditions", {}), f"exceptions[{i}].conditions", cond_warnings):
            warnings.extend(cond_warnings)
            continue
        try:
            exceptions.append(ExtractedException.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"exceptions[{i}]: {exc}")

    return ExtractionResult(
        rules=rules, definitions=definitions, exceptions=exceptions, warnings=warnings
    )
