"""Test fixtures.

Integration tests run against a real PostgreSQL database (a dedicated
`changegraph_test` database on the same server as development, created
automatically if missing) rather than mocks -- the engine relies on
PostgreSQL JSONB columns, and testing against SQLite would not exercise the
real storage layer.
"""

from __future__ import annotations

import os

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import *  # noqa: F401,F403 -- registers every table on Base.metadata,
# regardless of which test module happens to run (or be collected) first.

BASE_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://changegraph:changegraph@localhost:55432/changegraph"
)


def _test_database_url() -> str:
    # Swap the database name in the configured URL for a dedicated test DB.
    prefix, _, _ = BASE_DATABASE_URL.rpartition("/")
    return f"{prefix}/changegraph_test"


def _admin_connection_params() -> dict:
    prefix, _, _ = BASE_DATABASE_URL.rpartition("/")
    # postgresql+psycopg://user:pass@host:port -> psycopg connection string
    url_no_scheme = prefix.split("://", 1)[1]
    userpass, hostport = url_no_scheme.split("@")
    user, password = userpass.split(":")
    host, port = hostport.split(":")
    return {"host": host, "port": int(port), "user": user, "password": password, "dbname": "postgres"}


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_database():
    params = _admin_connection_params()
    conn = psycopg.connect(**params, autocommit=True)
    try:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", ("changegraph_test",)
        ).fetchone()
        if not exists:
            conn.execute("CREATE DATABASE changegraph_test")
    finally:
        conn.close()

    engine = create_engine(_test_database_url(), future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


_TEST_ENGINE = create_engine(_test_database_url(), future=True)
_TestSessionLocal = sessionmaker(bind=_TEST_ENGINE, autoflush=False, autocommit=False, future=True)


@pytest.fixture()
def db_session():
    # Routes under test call db.commit() themselves, so isolation is done by
    # truncating all tables before each test rather than wrapping tests in a
    # rolled-back transaction (which would conflict with those commits).
    with _TEST_ENGINE.begin() as conn:
        tables = Base.metadata.sorted_tables
        assert tables, "No tables registered on Base.metadata -- app.models failed to import"
        table_names = ", ".join(f'"{t.name}"' for t in reversed(tables))
        conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))

    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


class _NonClosingSession:
    """Delegates everything to a shared session except close().

    CompileJobService._run() always closes the session it opens (correct
    for its normal per-job session), but in eager test mode it must reuse
    the test's own db_session -- closing that out from under the test would
    break every assertion the test makes on db_session afterward.
    """

    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    def close(self):
        pass


@pytest.fixture()
def client(db_session, monkeypatch):
    from fastapi.testclient import TestClient

    from app.compiler.llm_provider import MockLLMProvider, get_llm_provider
    from app.database import get_db
    from app.main import app
    from app.services.compile_job_service import CompileJobService, get_compile_job_service

    def _override_get_db():
        yield db_session

    # Tests must be hermetic regardless of the ambient LLM_PROVIDER setting
    # (e.g. a developer's .env pointing at Bedrock with real AWS credentials)
    # -- always compile through the deterministic mock here.
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_llm_provider] = lambda: MockLLMProvider()
    # Compile jobs normally run as a backgrounded asyncio task. Tests need the
    # job fully finished (and persisted to db_session) by the time the compile
    # endpoint's response comes back, so they run eagerly here -- same code
    # path as production, just not deferred -- against the test's own session
    # rather than the real SessionLocal (which points at the dev database).
    app.dependency_overrides[get_compile_job_service] = lambda: CompileJobService(
        session_factory=lambda: _NonClosingSession(db_session), eager=True
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
