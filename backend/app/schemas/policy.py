import uuid

from pydantic import BaseModel, ConfigDict


class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    owner: str | None
    version: str
    source_text: str | None


class WorkflowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    implementation_reference: str | None
    status: str
