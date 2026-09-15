import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.evaluation import Decision, EvaluationRecord
from app.models.impact import ImpactAnalysis, ImpactItem
from app.schemas.impact import (
    DecisionChangeOut,
    ImpactAnalysisCreate,
    ImpactAnalysisDetailOut,
    ImpactAnalysisOut,
)
from app.services.impact_service import ImpactAnalysisError, create_impact_analysis, run_re_evaluation

router = APIRouter(prefix="/api/impact-analysis", tags=["impact-analysis"])


@router.get("", response_model=list[ImpactAnalysisOut])
def list_impact_analyses(db: Session = Depends(get_db)):
    return db.query(ImpactAnalysis).order_by(ImpactAnalysis.created_at.desc()).all()


@router.post("", response_model=ImpactAnalysisDetailOut, status_code=201)
def create_impact_analysis_endpoint(payload: ImpactAnalysisCreate, db: Session = Depends(get_db)):
    try:
        analysis = create_impact_analysis(db, payload.old_version_id, payload.new_version_id)
    except ImpactAnalysisError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(analysis)
    items = db.query(ImpactItem).filter(ImpactItem.impact_analysis_id == analysis.id).all()
    return ImpactAnalysisDetailOut(**ImpactAnalysisOut.model_validate(analysis).model_dump(), items=items)


@router.get("/{impact_analysis_id}", response_model=ImpactAnalysisDetailOut)
def get_impact_analysis(impact_analysis_id: uuid.UUID, db: Session = Depends(get_db)):
    analysis = db.get(ImpactAnalysis, impact_analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Impact analysis not found")
    items = db.query(ImpactItem).filter(ImpactItem.impact_analysis_id == analysis.id).all()
    return ImpactAnalysisDetailOut(**ImpactAnalysisOut.model_validate(analysis).model_dump(), items=items)


@router.post("/{impact_analysis_id}/re-evaluate", response_model=ImpactAnalysisDetailOut)
def re_evaluate_endpoint(impact_analysis_id: uuid.UUID, db: Session = Depends(get_db)):
    analysis = db.get(ImpactAnalysis, impact_analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Impact analysis not found")
    try:
        analysis = run_re_evaluation(db, analysis)
    except ImpactAnalysisError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(analysis)
    items = db.query(ImpactItem).filter(ImpactItem.impact_analysis_id == analysis.id).all()
    return ImpactAnalysisDetailOut(**ImpactAnalysisOut.model_validate(analysis).model_dump(), items=items)


@router.get("/{impact_analysis_id}/decisions", response_model=list[DecisionChangeOut])
def list_decision_changes(impact_analysis_id: uuid.UUID, db: Session = Depends(get_db)):
    analysis = db.get(ImpactAnalysis, impact_analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Impact analysis not found")

    new_decisions = (
        db.query(Decision)
        .filter(
            Decision.regulation_version_id == analysis.regulation_version_id,
            Decision.changed_from_decision_id.isnot(None),
        )
        .all()
    )
    if not new_decisions:
        return []

    old_ids = [d.changed_from_decision_id for d in new_decisions]
    old_decisions = {d.id: d for d in db.query(Decision).filter(Decision.id.in_(old_ids)).all()}

    record_ids = {d.evaluation_record_id for d in new_decisions}
    records = {
        r.id: r
        for r in db.query(EvaluationRecord).filter(EvaluationRecord.id.in_(record_ids)).all()
    }

    impact_reasons = {
        item.entity_id: item.explanation
        for item in db.query(ImpactItem).filter(
            ImpactItem.impact_analysis_id == impact_analysis_id,
            ImpactItem.entity_type == "DECISION",
        )
    }

    results: list[DecisionChangeOut] = []
    for new_decision in new_decisions:
        old_decision = old_decisions.get(new_decision.changed_from_decision_id)
        if old_decision is None or old_decision.regulation_version_id != analysis.compared_to_version_id:
            continue
        record = records.get(new_decision.evaluation_record_id)
        changed = old_decision.verdict != new_decision.verdict
        results.append(
            DecisionChangeOut(
                record_reference=record.external_reference if record else "unknown",
                jurisdiction=record.jurisdiction if record else "unknown",
                old_decision_id=old_decision.id,
                new_decision_id=new_decision.id,
                old_verdict=old_decision.verdict,
                new_verdict=new_decision.verdict,
                changed=changed,
                reason=impact_reasons.get(new_decision.id, "No verdict change." if not changed else "Verdict changed."),
            )
        )

    return results
