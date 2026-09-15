import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompileJobChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    status: str
    char_start: int
    char_end: int
    rules_extracted: int
    definitions_extracted: int
    exceptions_extracted: int
    warnings: list[str]
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CompileJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    regulation_id: uuid.UUID
    regulation_version_id: uuid.UUID
    status: str
    current_step: str | None
    chunks_total: int
    chunks_completed: int
    chunks_failed: int
    llm_provider: str
    error_message: str | None
    result: dict | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    chunks: list[CompileJobChunkOut] = Field(default_factory=list)
