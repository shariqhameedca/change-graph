"""Drives a compile end to end as a job: chunk -> per-chunk LLM extraction ->
merge -> persist, with progress tracked on CompileJob/CompileJobChunk rows.

This is the boundary that decides *how* a job executes (inline for tests /
eager mode, or as a backgrounded asyncio task otherwise) -- everything else
(the CompileJob/CompileJobChunk schema, the /api/jobs status endpoint) stays
the same regardless, so swapping the runner for a real task queue later would
only touch this file.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.compiler.chunker import chunk_regulation_text
from app.compiler.llm_provider import LLMProvider
from app.compiler.merger import ChunkExtraction, merge_chunk_extractions
from app.compiler.validator import validate_extraction
from app.config import get_settings
from app.database import SessionLocal
from app.models.compile_job import CompileJob, CompileJobChunk
from app.models.regulation import Regulation, RegulationVersion
from app.services.compiler_service import persist_extraction

logger = logging.getLogger(__name__)

_RAW_RESPONSE_LOG_CAP = 20_000  # keep chunk rows bounded; enough for debugging truncation issues

TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "COMPLETED_WITH_WARNINGS", "CANCELLED"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CompileJobService:
    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
        eager: bool = False,
    ):
        self._session_factory = session_factory
        self._eager = eager
        self._background_tasks: set[asyncio.Task] = set()

    def create_job(
        self,
        db: Session,
        regulation: Regulation,
        version: RegulationVersion,
        provider_name: str,
    ) -> CompileJob:
        """Chunk the version's source text and insert the job + one chunk row
        per piece, on the caller's own session. No LLM calls happen here --
        this is cheap, synchronous, and safe to run inline in the request."""
        chunks = chunk_regulation_text(version.source_text)

        job = CompileJob(
            regulation_id=regulation.id,
            regulation_version_id=version.id,
            status="QUEUED",
            chunks_total=len(chunks),
            llm_provider=provider_name,
        )
        db.add(job)
        db.flush()

        for chunk in chunks:
            db.add(
                CompileJobChunk(
                    compile_job_id=job.id,
                    chunk_index=chunk.index,
                    status="PENDING",
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                )
            )
        db.commit()
        db.refresh(job)
        return job

    async def start(self, job_id: uuid.UUID, provider: LLMProvider) -> None:
        if self._eager:
            await self._run(job_id, provider)
            return

        task = asyncio.create_task(self._run(job_id, provider))
        self._background_tasks.add(task)

        def _on_done(t: asyncio.Task) -> None:
            self._background_tasks.discard(t)
            if not t.cancelled() and t.exception() is not None:
                logger.error("Compile job %s crashed outside its own handling", job_id, exc_info=t.exception())

        task.add_done_callback(_on_done)

    async def _run(self, job_id: uuid.UUID, provider: LLMProvider) -> None:
        db = self._session_factory()
        try:
            job = db.get(CompileJob, job_id)
            if job is None:
                logger.error("Compile job %s vanished before it could run", job_id)
                return

            job.status = "RUNNING"
            job.started_at = _now()
            db.commit()

            regulation = db.get(Regulation, job.regulation_id)
            version = db.get(RegulationVersion, job.regulation_version_id)
            source_text = version.source_text
            chunk_rows = (
                db.query(CompileJobChunk)
                .filter(CompileJobChunk.compile_job_id == job.id)
                .order_by(CompileJobChunk.chunk_index)
                .all()
            )

            successful: list[ChunkExtraction] = []
            for row in chunk_rows:
                job.current_step = f"Extracting chunk {row.chunk_index + 1} of {len(chunk_rows)}"
                row.status = "RUNNING"
                row.started_at = _now()
                db.commit()

                try:
                    raw = await provider.generate_structured(
                        source_text[row.char_start : row.char_end], regulation.jurisdiction
                    )
                    extraction = validate_extraction(raw)
                except Exception as exc:  # noqa: BLE001 - one chunk's failure must not abort the job
                    row.status = "FAILED"
                    row.error_message = str(exc)
                    job.chunks_failed += 1
                    logger.warning("Compile job %s chunk %s failed: %s", job.id, row.chunk_index, exc)
                else:
                    row.status = "SUCCEEDED"
                    row.rules_extracted = len(extraction.rules)
                    row.definitions_extracted = len(extraction.definitions)
                    row.exceptions_extracted = len(extraction.exceptions)
                    row.warnings = list(extraction.warnings)
                    # default=str: MockLLMProvider's raw dicts can contain native
                    # date objects (a real LLM's raw text is already valid JSON,
                    # so this only ever engages for the mock/demo path).
                    row.raw_response = json.dumps(raw, default=str)[:_RAW_RESPONSE_LOG_CAP]
                    successful.append(
                        ChunkExtraction(
                            chunk_index=row.chunk_index,
                            rules=extraction.rules,
                            definitions=extraction.definitions,
                            exceptions=extraction.exceptions,
                            warnings=extraction.warnings,
                        )
                    )

                row.completed_at = _now()
                job.chunks_completed += 1
                db.commit()

            if not successful:
                job.status = "FAILED"
                job.error_message = "All chunks failed to extract -- see per-chunk errors for detail."
                job.current_step = None
                job.completed_at = _now()
                db.commit()
                return

            job.current_step = "Merging and persisting results"
            db.commit()

            merged = merge_chunk_extractions(successful)
            for row in chunk_rows:
                if row.status == "FAILED":
                    merged.warnings.append(
                        f"[chunk {row.chunk_index + 1}/{len(chunk_rows)}] This chunk failed and was "
                        f"skipped: {row.error_message}"
                    )

            try:
                report = persist_extraction(db, regulation, version, merged)
                db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                job.status = "FAILED"
                job.error_message = f"Persisting compiled results failed: {exc}"
                job.current_step = None
                job.completed_at = _now()
                db.commit()
                return

            job.result = report
            job.current_step = None
            job.completed_at = _now()
            job.status = "SUCCEEDED" if job.chunks_failed == 0 and not report["warnings"] else "COMPLETED_WITH_WARNINGS"
            db.commit()
        finally:
            db.close()


def reconcile_interrupted_jobs(db: Session) -> int:
    """Marks any job left QUEUED/RUNNING as FAILED. An in-process asyncio
    task is simply abandoned on process exit, so without this a job could
    stay stuck RUNNING forever after a server restart."""
    jobs = db.query(CompileJob).filter(CompileJob.status.in_(["QUEUED", "RUNNING"])).all()
    for job in jobs:
        job.status = "FAILED"
        job.error_message = "Interrupted by server restart."
        job.completed_at = _now()
    db.commit()
    return len(jobs)


def get_compile_job_service() -> CompileJobService:
    settings = get_settings()
    return CompileJobService(eager=settings.compile_jobs_eager)
