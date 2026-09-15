import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ExceptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_id: uuid.UUID
    description: str
    conditions: dict[str, Any]
    source_reference: str | None
    source_text: str | None


class DefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    regulation_version_id: uuid.UUID
    term: str
    definition: str
    source_reference: str | None
    source_text: str | None


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    regulation_version_id: uuid.UUID
    rule_code: str
    title: str
    description: str | None
    rule_type: str
    priority: int
    jurisdiction: str
    effective_from: date
    effective_to: date | None
    conditions: dict[str, Any]
    actions: dict[str, Any]
    source_reference: str | None
    source_text: str | None
    confidence: float
    created_at: datetime
    updated_at: datetime


class RuleDetailOut(RuleOut):
    exceptions: list[ExceptionOut] = []
    affected_decision_count: int = 0


class ConflictFinding(BaseModel):
    type: str
    rule_a: str
    rule_b: str
    description: str
