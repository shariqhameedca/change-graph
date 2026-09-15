from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.engine.decision_service import evaluate_record
from app.models.evaluation import Decision, EvaluationRecord
from app.models.regulation import RegulationVersion
from app.schemas.evaluation import EvaluateAdHocRequest, EvaluateRequest, EvaluateResponse
from app.services.decision_service import evaluate_and_persist
from app.services.rule_service import load_rules_for_version

router = APIRouter(prefix="/api/evaluate", tags=["evaluate"])


def _serialize_trace(entry: dict) -> dict:
    return {
        "rule_id": str(entry["rule_id"]),
        "rule_code": entry["rule_code"],
        "title": entry["title"],
        "applicable": entry["applicable"],
        "evaluation_result": entry["evaluation_result"],
        "explanation": entry["explanation"],
        "action": entry["action"],
        "condition_result": entry["condition_result"],
        "exception_matched": entry["exception_matched"],
        "source_reference": entry["source_reference"],
        "source_text": entry["source_text"],
    }


@router.post("", response_model=EvaluateResponse)
def evaluate(payload: EvaluateRequest, db: Session = Depends(get_db)):
    record = db.get(EvaluationRecord, payload.record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Evaluation record not found")
    version = db.get(RegulationVersion, payload.regulation_version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Regulation version not found")

    # A prior decision for this exact record + version is superseded, not duplicated.
    previous = (
        db.query(Decision)
        .filter(
            Decision.evaluation_record_id == record.id,
            Decision.regulation_version_id == version.id,
        )
        .order_by(Decision.evaluated_at.desc())
        .first()
    )

    decision, result = evaluate_and_persist(
        db, record, version, changed_from_decision_id=None if previous is None else previous.id
    )
    db.commit()

    return EvaluateResponse(
        decision_id=decision.id,
        verdict=result["verdict"],
        summary=result["summary"],
        rules_evaluated=result["rules_evaluated"],
        rules_applicable=result["rules_applicable"],
        rules_fired=result["rules_fired"],
        trace=[_serialize_trace(e) for e in result["trace"]],
    )


@router.post("/simulate", response_model=EvaluateResponse)
def evaluate_simulate(payload: EvaluateAdHocRequest, db: Session = Depends(get_db)):
    """Evaluates ad-hoc input against a regulation version without persisting
    anything -- used by the What-if Scenario Simulator."""

    version = db.get(RegulationVersion, payload.regulation_version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Regulation version not found")

    rules = load_rules_for_version(db, version.id)
    data = dict(payload.input_data)
    data.setdefault("jurisdiction", payload.jurisdiction)
    result = evaluate_record(rules, data, as_of=version.effective_from)

    return EvaluateResponse(
        decision_id=None,
        verdict=result["verdict"],
        summary=result["summary"],
        rules_evaluated=result["rules_evaluated"],
        rules_applicable=result["rules_applicable"],
        rules_fired=result["rules_fired"],
        trace=[_serialize_trace(e) for e in result["trace"]],
    )
