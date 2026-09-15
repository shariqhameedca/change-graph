import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    decisions,
    documents,
    evaluate,
    evaluation_suite,
    graph,
    health,
    impact,
    jobs,
    records,
    regulations,
    rules,
)
from app.config import get_settings
from app.database import SessionLocal
from app.services.compile_job_service import reconcile_interrupted_jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("changegraph")

settings = get_settings()

app = FastAPI(
    title="ChangeGraph",
    description=(
        "Regulatory intelligence and deterministic decision engine. "
        "Synthetic demonstration data only -- not legal advice."
    ),
    version=settings.engine_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _reconcile_interrupted_compile_jobs() -> None:
    # An in-process asyncio compile job is abandoned (not resumed) if the
    # server restarts mid-run -- without this, its row would stay stuck at
    # RUNNING forever with nothing left to ever finish it. Best-effort: this
    # must never block app startup (e.g. before the compile_jobs migration
    # has been applied yet, or the DB is briefly unreachable).
    db = SessionLocal()
    try:
        count = reconcile_interrupted_jobs(db)
        if count:
            logger.warning("Marked %d interrupted compile job(s) as FAILED on startup", count)
    except Exception:  # noqa: BLE001
        logger.warning("Could not reconcile interrupted compile jobs on startup", exc_info=True)
    finally:
        db.close()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Invalid request", "errors": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    return await http_exception_handler(request, exc)


app.include_router(health.router, prefix="/api")
app.include_router(regulations.router)
app.include_router(rules.router)
app.include_router(records.router)
app.include_router(evaluate.router)
app.include_router(decisions.router)
app.include_router(impact.router)
app.include_router(graph.router)
app.include_router(evaluation_suite.router)
app.include_router(documents.router)
app.include_router(jobs.router)
