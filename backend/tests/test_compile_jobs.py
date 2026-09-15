"""Tests for the async, chunked compile job pipeline: chunking, merging,
background execution with real progress, partial-chunk failure handling, and
startup reconciliation of interrupted jobs.
"""

from __future__ import annotations

import asyncio
import time
from datetime import date

import pytest

from app.compiler.chunker import chunk_regulation_text
from app.compiler.merger import ChunkExtraction, merge_chunk_extractions
from app.compiler.validator import ExtractedException, ExtractedRule
from app.models.compile_job import CompileJob
from app.services.compile_job_service import CompileJobService, reconcile_interrupted_jobs
from tests.conftest import _NonClosingSession

# Three paragraphs sized so each one alone is close to the ~12k char budget,
# forcing the chunker to produce exactly three chunks (one per paragraph)
# rather than packing multiple paragraphs into one chunk.
_LONG_SOURCE_TEXT = "\n\n".join(
    f"Paragraph {i}. " + ("Regulatory text describing a requirement. " * 160) for i in range(3)
)


def _valid_rule_dict(code: str) -> dict:
    return {
        "rule_code": code,
        "title": f"Rule {code}",
        "rule_type": "GENERAL",
        "priority": 100,
        "jurisdiction": "ANY",
        "effective_from": "2024-01-01",
        "effective_to": None,
        "conditions": {"all": [{"field": "loan.apr", "operator": "greater_than", "value": 10}]},
        "actions": {"verdict": "FAIL", "action": "REJECT", "message": "x"},
        "source_reference": None,
        "source_text": None,
        "confidence": 0.9,
    }


class FakeSlowLLMProvider:
    """Returns one distinct valid rule per call, after an artificial delay."""

    def __init__(self, delay: float = 0.3):
        self.delay = delay
        self.call_count = 0

    async def generate_structured(self, source_text: str, jurisdiction: str) -> dict:
        self.call_count += 1
        await asyncio.sleep(self.delay)
        return {
            "rules": [_valid_rule_dict(f"RULE-{self.call_count:03d}")],
            "definitions": [],
            "exceptions": [],
            "warnings": [],
        }


class FlakyLLMProvider:
    """Fails only on its second call (i.e. chunk index 1)."""

    def __init__(self):
        self.call_count = 0

    async def generate_structured(self, source_text: str, jurisdiction: str) -> dict:
        self.call_count += 1
        if self.call_count == 2:
            raise RuntimeError("simulated transient failure")
        return {
            "rules": [_valid_rule_dict(f"RULE-{self.call_count:03d}")],
            "definitions": [],
            "exceptions": [],
            "warnings": [],
        }


@pytest.fixture()
def async_client(db_session):
    """A TestClient variant with a real (non-eager) job service and a
    swappable LLM provider, for tests that need to observe a job actually
    running in the background rather than completing inline."""
    from fastapi.testclient import TestClient

    from app.compiler.llm_provider import get_llm_provider
    from app.database import get_db
    from app.main import app
    from app.services.compile_job_service import get_compile_job_service

    def _override_get_db():
        yield db_session

    def make(provider) -> TestClient:
        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_llm_provider] = lambda: provider
        app.dependency_overrides[get_compile_job_service] = lambda: CompileJobService(
            session_factory=lambda: db_session, eager=False
        )
        return TestClient(app)

    yield make
    app.dependency_overrides.clear()


def _create_regulation_and_version(client, source_text: str = _LONG_SOURCE_TEXT) -> tuple[str, str]:
    reg = client.post(
        "/api/regulations", json={"name": "Async Test Regulation", "jurisdiction": "United States"}
    ).json()
    version = client.post(
        f"/api/regulations/{reg['id']}/versions",
        json={"version": "1.0", "effective_from": "2024-01-01", "source_text": source_text},
    ).json()
    return reg["id"], version["id"]


def _poll_until_terminal(client, job_id: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    terminal = {"SUCCEEDED", "FAILED", "COMPLETED_WITH_WARNINGS", "CANCELLED"}
    last = None
    while time.monotonic() < deadline:
        last = client.get(f"/api/jobs/{job_id}").json()
        if last["status"] in terminal:
            return last
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} did not reach a terminal state in time: {last}")


def test_compile_returns_job_immediately_in_async_mode(async_client):
    provider = FakeSlowLLMProvider(delay=0.3)
    with async_client(provider) as client:
        reg_id, version_id = _create_regulation_and_version(client, source_text="Short text with one rule.")
        started = time.monotonic()
        resp = client.post(f"/api/regulations/{reg_id}/versions/{version_id}/compile")
        elapsed = time.monotonic() - started

        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] in ("QUEUED", "RUNNING")
        assert elapsed < 0.3, "compile should return before the (slow) LLM call finishes"

        final = _poll_until_terminal(client, body["id"])
        assert final["status"] in ("SUCCEEDED", "COMPLETED_WITH_WARNINGS")
        assert final["result"]["rules_created"] == 1


def test_compile_progress_advances_across_polls(async_client):
    provider = FakeSlowLLMProvider(delay=0.2)
    with async_client(provider) as client:
        reg_id, version_id = _create_regulation_and_version(client)
        resp = client.post(f"/api/regulations/{reg_id}/versions/{version_id}/compile")
        job_id = resp.json()["id"]
        assert resp.json()["chunks_total"] >= 2, "test text must force multiple chunks"

        seen_completed: list[int] = []
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            status = client.get(f"/api/jobs/{job_id}").json()
            seen_completed.append(status["chunks_completed"])
            if status["status"] in ("SUCCEEDED", "FAILED", "COMPLETED_WITH_WARNINGS"):
                break
            time.sleep(0.05)

        assert seen_completed == sorted(seen_completed), "chunks_completed must never decrease"
        assert seen_completed[-1] == resp.json()["chunks_total"]
        assert len(set(seen_completed)) > 1, "progress should have advanced across at least two distinct values"


def test_multi_chunk_merge_renumbers_colliding_rule_codes():
    rule_a = ExtractedRule.model_validate(_valid_rule_dict("RULE-001"))
    rule_b = ExtractedRule.model_validate(_valid_rule_dict("RULE-001"))
    exception_b = ExtractedException(
        rule_code="RULE-001",
        description="carve-out",
        conditions={"all": [{"field": "loan.apr", "operator": "greater_than", "value": 10}]},
    )

    merged = merge_chunk_extractions(
        [
            ChunkExtraction(chunk_index=0, rules=[rule_a]),
            ChunkExtraction(chunk_index=1, rules=[rule_b], exceptions=[exception_b]),
        ]
    )

    codes = [r.rule_code for r in merged.rules]
    assert codes[0] == "RULE-001"
    assert codes[1] == "RULE-001-C2"
    assert merged.exceptions[0].rule_code == "RULE-001-C2"
    assert any("renumbered" in w for w in merged.warnings)


def test_chunker_respects_paragraph_boundaries():
    paragraphs = [f"Paragraph {i} content here, more words to pad it out further." for i in range(20)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_regulation_text(text, char_budget=200)

    assert len(chunks) > 1
    for chunk in chunks:
        assert text[chunk.char_start : chunk.char_end] == chunk.text
    for paragraph in paragraphs:
        assert any(paragraph in chunk.text for chunk in chunks), f"paragraph split across chunks: {paragraph!r}"


@pytest.mark.asyncio
async def test_failed_chunk_does_not_fail_whole_job(db_session):
    from app.models.regulation import Regulation, RegulationVersion
    from app.services.regulation_service import create_regulation, create_version

    regulation = create_regulation(db_session, "Flaky Test Regulation", None, "United States", None)
    db_session.commit()
    version = create_version(
        db_session, regulation, "1.0", date(2024, 1, 1), None, "DRAFT", _LONG_SOURCE_TEXT
    )
    db_session.commit()

    service = CompileJobService(session_factory=lambda: _NonClosingSession(db_session), eager=True)
    provider = FlakyLLMProvider()
    job = service.create_job(db_session, regulation, version, provider_name="FlakyLLMProvider")
    assert job.chunks_total >= 2, "test text must force multiple chunks"

    await service.start(job.id, provider)

    db_session.refresh(job)
    assert job.status == "COMPLETED_WITH_WARNINGS"
    assert job.chunks_failed == 1
    assert job.result["rules_created"] >= 1


def test_interrupted_jobs_marked_failed_on_startup(db_session):
    from app.models.regulation import Regulation, RegulationVersion
    from app.services.regulation_service import create_regulation, create_version

    regulation = create_regulation(db_session, "Interrupted Test Regulation", None, "United States", None)
    db_session.commit()
    version = create_version(
        db_session, regulation, "1.0", date(2024, 1, 1), None, "DRAFT", "Short text."
    )
    db_session.commit()

    job = CompileJob(
        regulation_id=regulation.id,
        regulation_version_id=version.id,
        status="RUNNING",
        chunks_total=1,
        llm_provider="MockLLMProvider",
    )
    db_session.add(job)
    db_session.commit()

    count = reconcile_interrupted_jobs(db_session)
    assert count == 1

    db_session.refresh(job)
    assert job.status == "FAILED"
    assert job.completed_at is not None
