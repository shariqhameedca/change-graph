import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import uuid_pk


class CompileJob(Base):
    """Tracks one compile attempt for a regulation version.

    A job is chunked up front (see app.compiler.chunker), so its progress is
    just chunks_completed/chunks_total -- no separate progress concept needed.
    """

    __tablename__ = "compile_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    regulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regulations.id"), nullable=False
    )
    regulation_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regulation_versions.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED")
    current_step: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunks_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunks_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunks_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chunks: Mapped[list["CompileJobChunk"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="CompileJobChunk.chunk_index"
    )


class CompileJobChunk(Base):
    """One LLM extraction call's worth of work within a CompileJob."""

    __tablename__ = "compile_job_chunks"
    __table_args__ = (UniqueConstraint("compile_job_id", "chunk_index"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    compile_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compile_jobs.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    definitions_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exceptions_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["CompileJob"] = relationship(back_populates="chunks")
