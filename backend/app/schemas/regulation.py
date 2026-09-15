import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class RegulationCreate(BaseModel):
    name: str
    description: str | None = None
    jurisdiction: str
    source_url: str | None = None


class RegulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    jurisdiction: str
    source_url: str | None
    created_at: datetime
    updated_at: datetime


class RegulationVersionCreate(BaseModel):
    version: str
    effective_from: date
    effective_to: date | None = None
    status: str = "DRAFT"
    source_text: str = ""


class RegulationVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    regulation_id: uuid.UUID
    version: str
    effective_from: date
    effective_to: date | None
    status: str
    source_text: str
    created_at: datetime


class RegulationDetailOut(RegulationOut):
    versions: list[RegulationVersionOut] = Field(default_factory=list)


class CompilationReport(BaseModel):
    rules_created: int
    definitions_created: int
    exceptions_created: int
    relationships_created: int
    warnings: list[str]


class DeletePreviewOut(BaseModel):
    versions: int
    rules: int
    decisions: int
    impact_analyses: int
