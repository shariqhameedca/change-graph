import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ImpactAnalysisCreate(BaseModel):
    old_version_id: uuid.UUID
    new_version_id: uuid.UUID


class ImpactItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    impact_analysis_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    impact_type: str
    severity: str
    explanation: str


class ImpactAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    regulation_version_id: uuid.UUID
    compared_to_version_id: uuid.UUID
    status: str
    summary: dict[str, Any]
    created_at: datetime


class ImpactAnalysisDetailOut(ImpactAnalysisOut):
    items: list[ImpactItemOut] = []


class DecisionChangeOut(BaseModel):
    record_reference: str
    jurisdiction: str
    old_decision_id: uuid.UUID
    new_decision_id: uuid.UUID
    old_verdict: str
    new_verdict: str
    changed: bool
    reason: str
