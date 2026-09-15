import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.evaluation import Decision, DecisionTrace
from app.models.rule import Rule
from app.schemas.evaluation import DecisionDetailOut, DecisionOut, DecisionTraceOut

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.get("", response_model=list[DecisionOut])
def list_decisions(
    regulation_version_id: uuid.UUID | None = Query(default=None),
    evaluation_record_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(Decision)
    if regulation_version_id is not None:
        query = query.filter(Decision.regulation_version_id == regulation_version_id)
    if evaluation_record_id is not None:
        query = query.filter(Decision.evaluation_record_id == evaluation_record_id)
    return query.order_by(Decision.evaluated_at.desc()).limit(limit).all()


@router.get("/{decision_id}", response_model=DecisionDetailOut)
def get_decision(decision_id: uuid.UUID, db: Session = Depends(get_db)):
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    trace = db.query(DecisionTrace).filter(DecisionTrace.decision_id == decision_id).all()
    rules_by_id = {
        r.id: r for r in db.query(Rule).filter(Rule.id.in_([t.rule_id for t in trace])).all()
    } if trace else {}

    trace_out = []
    for t in trace:
        rule = rules_by_id.get(t.rule_id)
        trace_out.append(
            DecisionTraceOut(
                **DecisionTraceOut.model_validate(t).model_dump(exclude={"rule_code", "rule_title"}),
                rule_code=rule.rule_code if rule else "",
                rule_title=rule.title if rule else "",
            )
        )

    return DecisionDetailOut(**DecisionOut.model_validate(decision).model_dump(), trace=trace_out)
