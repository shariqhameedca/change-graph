import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.compile_job import CompileJob
from app.schemas.compile_job import CompileJobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=CompileJobOut)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.get(CompileJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
