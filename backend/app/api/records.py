import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.evaluation import EvaluationRecord
from app.schemas.evaluation import EvaluationRecordOut

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("", response_model=list[EvaluationRecordOut])
def list_records(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return (
        db.query(EvaluationRecord)
        .order_by(EvaluationRecord.created_at)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{record_id}", response_model=EvaluationRecordOut)
def get_record(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record = db.get(EvaluationRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record
