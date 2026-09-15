import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.evaluation import Decision, DecisionTrace
from app.models.rule import Rule, RuleException
from app.schemas.rule import ConflictFinding, RuleDetailOut, RuleOut
from app.services.conflict_service import analyze_conflicts

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def list_rules(
    regulation_version_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Rule)
    if regulation_version_id is not None:
        query = query.filter(Rule.regulation_version_id == regulation_version_id)
    return query.order_by(Rule.priority, Rule.rule_code).all()


@router.get("/{rule_id}", response_model=RuleDetailOut)
def get_rule(rule_id: uuid.UUID, db: Session = Depends(get_db)):
    rule = db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    exceptions = db.query(RuleException).filter(RuleException.rule_id == rule_id).all()
    affected_decision_count = (
        db.query(DecisionTrace)
        .join(Decision, Decision.id == DecisionTrace.decision_id)
        .filter(DecisionTrace.rule_id == rule_id, DecisionTrace.evaluation_result == "MATCH")
        .count()
    )

    return RuleDetailOut(
        **RuleOut.model_validate(rule).model_dump(),
        exceptions=exceptions,
        affected_decision_count=affected_decision_count,
    )


@router.post("/conflicts/analyze", response_model=list[ConflictFinding])
def analyze_conflicts_endpoint(
    regulation_version_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return analyze_conflicts(db, regulation_version_id)
