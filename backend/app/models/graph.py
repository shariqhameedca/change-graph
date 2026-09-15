import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import uuid_pk

# node_type values: REGULATION, VERSION, DEFINITION, RULE, EXCEPTION, POLICY,
# WORKFLOW, DECISION, RECORD
# relationship_type values: DEFINES, DEPENDS_ON, APPLIES_TO, HAS_EXCEPTION,
# IMPLEMENTS, DERIVED_FROM, AFFECTS, SUPERSEDES, REQUIRES, TRIGGERS


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id: Mapped[uuid.UUID] = uuid_pk()
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    node_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"

    id: Mapped[uuid.UUID] = uuid_pk()
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    edge_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
