import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import TimestampMixin, uuid_pk


class Regulation(Base, TimestampMixin):
    __tablename__ = "regulations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    versions: Mapped[list["RegulationVersion"]] = relationship(
        back_populates="regulation",
        cascade="all, delete-orphan",
        order_by="RegulationVersion.created_at",
    )


class RegulationVersion(Base):
    __tablename__ = "regulation_versions"

    id: Mapped[uuid.UUID] = uuid_pk()
    regulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regulations.id"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    source_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )

    regulation: Mapped["Regulation"] = relationship(back_populates="versions")
    rules: Mapped[list["Rule"]] = relationship(
        back_populates="regulation_version", cascade="all, delete-orphan"
    )
    definitions: Mapped[list["Definition"]] = relationship(
        back_populates="regulation_version", cascade="all, delete-orphan"
    )


from app.models.rule import Definition, Rule  # noqa: E402
