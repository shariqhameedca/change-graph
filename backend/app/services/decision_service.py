"""Persists deterministic decisions.

This is the boundary between the pure `app.engine` and the database: it
loads rules, calls the pure evaluator, and writes Decision + DecisionTrace
rows. The verdict itself is always produced by `app.engine.decision_service`.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.engine.decision_service import evaluate_record
from app.models.evaluation import Decision, DecisionTrace, EvaluationRecord
from app.models.regulation import RegulationVersion
from app.services.rule_service import load_rules_for_version


def record_to_engine_input(record: EvaluationRecord) -> dict:
    """The engine reads a top-level `jurisdiction` key for applicability
    checks; that field lives on EvaluationRecord itself, not inside
    input_data, so it is merged in here rather than duplicated in storage."""

    return {**record.input_data, "jurisdiction": record.jurisdiction}


def evaluate_and_persist(
    db: Session,
    record: EvaluationRecord,
    regulation_version: RegulationVersion,
    changed_from_decision_id: uuid.UUID | None = None,
) -> tuple[Decision, dict]:
    settings = get_settings()
    rules = load_rules_for_version(db, regulation_version.id)
    data = record_to_engine_input(record)
    result = evaluate_record(rules, data, as_of=regulation_version.effective_from)

    decision = Decision(
        evaluation_record_id=record.id,
        regulation_version_id=regulation_version.id,
        verdict=result["verdict"],
        engine_version=settings.engine_version,
        summary=result["summary"],
        changed_from_decision_id=changed_from_decision_id,
    )
    db.add(decision)
    db.flush()

    for entry in result["trace"]:
        if not entry["applicable"]:
            continue
        db.add(
            DecisionTrace(
                decision_id=decision.id,
                rule_id=entry["rule_id"],
                evaluation_result=entry["evaluation_result"],
                input_snapshot=data,
                condition_results=_trace_conditions(entry),
                explanation=entry["explanation"],
                source_reference=entry["source_reference"],
                source_text=entry["source_text"],
            )
        )

    db.flush()
    return decision, result


def _json_safe(value: Any) -> Any:
    """Recursively converts UUIDs/dates to JSON-serializable primitives so
    engine output (which may carry UUID rule/exception ids) can be stored
    in a JSONB column."""

    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _trace_conditions(entry: dict) -> dict:
    return _json_safe(
        {
            "condition_result": entry["condition_result"],
            "exception_matched": entry["exception_matched"],
            "action": entry["action"],
        }
    )
