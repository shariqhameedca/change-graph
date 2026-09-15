import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import uuid_pk


# status values: PENDING, COMPLETED, FAILED
class ImpactAnalysis(Base):
    __tablename__ = "impact_analyses"

    id: Mapped[uuid.UUID] = uuid_pk()
    regulation_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regulation_versions.id"), nullable=False
    )
    compared_to_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regulation_versions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )


# entity_type values: RULE, DEFINITION, EXCEPTION, POLICY, WORKFLOW, DECISION
# impact_type values: ADDED, REMOVED, MODIFIED, AFFECTED, OUTCOME_CHANGED
# severity values: HIGH, MEDIUM, LOW
class ImpactItem(Base):
    __tablename__ = "impact_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    impact_analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("impact_analyses.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    impact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
