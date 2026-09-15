from typing import Any

from pydantic import BaseModel


class GraphNodeOut(BaseModel):
    id: str
    type: str
    entity_id: str
    label: str
    metadata: dict[str, Any]


class GraphEdgeOut(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    metadata: dict[str, Any]


class GraphOut(BaseModel):
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]
