import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import TimestampMixin, uuid_pk


class Rule(Base, TimestampMixin):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = uuid_pk()
    regulation_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regulation_versions.id"), nullable=False
    )
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, default="GENERAL")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    jurisdiction: Mapped[str] = mapped_column(String(120), nullable=False, default="ANY")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    actions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    regulation_version: Mapped["RegulationVersion"] = relationship(
        back_populates="rules"
    )
    exceptions: Mapped[list["RuleException"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class Definition(Base):
    __tablename__ = "definitions"

    id: Mapped[uuid.UUID] = uuid_pk()
    regulation_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regulation_versions.id"), nullable=False
    )
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    regulation_version: Mapped["RegulationVersion"] = relationship(
        back_populates="definitions"
    )


class RuleException(Base):
    """A carve-out from a Rule's applicability (spec entity name: Exception)."""

    __tablename__ = "exceptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule: Mapped["Rule"] = relationship(back_populates="exceptions")


from app.models.regulation import RegulationVersion  # noqa: E402
