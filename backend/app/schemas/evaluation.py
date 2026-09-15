import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EvaluationRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_reference: str
    jurisdiction: str
    record_type: str
    input_data: dict[str, Any]
    created_at: datetime


class EvaluateRequest(BaseModel):
    record_id: uuid.UUID
    regulation_version_id: uuid.UUID


class EvaluateAdHocRequest(BaseModel):
    """Used by the What-if Simulator to evaluate an unsaved record."""

    regulation_version_id: uuid.UUID
    input_data: dict[str, Any]
    jurisdiction: str = "ANY"


class DecisionTraceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    decision_id: uuid.UUID
    rule_id: uuid.UUID
    rule_code: str = ""
    rule_title: str = ""
    evaluation_result: str
    input_snapshot: dict[str, Any]
    condition_results: dict[str, Any]
    explanation: str
    source_reference: str | None
    source_text: str | None


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evaluation_record_id: uuid.UUID
    regulation_version_id: uuid.UUID
    verdict: str
    evaluated_at: datetime
    engine_version: str
    summary: str
    changed_from_decision_id: uuid.UUID | None


class DecisionDetailOut(DecisionOut):
    trace: list[DecisionTraceOut] = []


class EvaluateResponse(BaseModel):
    decision_id: uuid.UUID | None = None
    verdict: str
    summary: str
    rules_evaluated: int
    rules_applicable: int
    rules_fired: int
    trace: list[dict[str, Any]]
