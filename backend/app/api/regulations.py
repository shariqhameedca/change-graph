import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.compiler.llm_provider import LLMProvider, get_llm_provider
from app.models.regulation import Regulation, RegulationVersion
from app.models.rule import Definition, Rule, RuleException
from app.schemas.compile_job import CompileJobOut
from app.schemas.regulation import (
    DeletePreviewOut,
    RegulationCreate,
    RegulationDetailOut,
    RegulationOut,
    RegulationVersionCreate,
    RegulationVersionOut,
)
from app.schemas.rule import DefinitionOut, ExceptionOut
from app.services.compile_job_service import CompileJobService, get_compile_job_service
from app.services.regulation_service import (
    create_regulation,
    create_version,
    delete_regulation,
    preview_delete_regulation,
)

router = APIRouter(prefix="/api/regulations", tags=["regulations"])


@router.get("", response_model=list[RegulationOut])
def list_regulations(db: Session = Depends(get_db)):
    return db.query(Regulation).order_by(Regulation.name).all()


@router.post("", response_model=RegulationOut, status_code=201)
def create_regulation_endpoint(payload: RegulationCreate, db: Session = Depends(get_db)):
    regulation = create_regulation(
        db, payload.name, payload.description, payload.jurisdiction, payload.source_url
    )
    db.commit()
    db.refresh(regulation)
    return regulation


@router.get("/{regulation_id}", response_model=RegulationDetailOut)
def get_regulation(regulation_id: uuid.UUID, db: Session = Depends(get_db)):
    regulation = db.get(Regulation, regulation_id)
    if regulation is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
    return regulation


@router.get("/{regulation_id}/delete-preview", response_model=DeletePreviewOut)
def get_delete_preview(regulation_id: uuid.UUID, db: Session = Depends(get_db)):
    regulation = db.get(Regulation, regulation_id)
    if regulation is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
    return preview_delete_regulation(db, regulation)


@router.delete("/{regulation_id}", status_code=204)
def delete_regulation_endpoint(regulation_id: uuid.UUID, db: Session = Depends(get_db)):
    regulation = db.get(Regulation, regulation_id)
    if regulation is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
    delete_regulation(db, regulation)
    db.commit()


@router.get("/{regulation_id}/versions", response_model=list[RegulationVersionOut])
def list_versions(regulation_id: uuid.UUID, db: Session = Depends(get_db)):
    regulation = db.get(Regulation, regulation_id)
    if regulation is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
    return (
        db.query(RegulationVersion)
        .filter(RegulationVersion.regulation_id == regulation_id)
        .order_by(RegulationVersion.created_at)
        .all()
    )


@router.get("/{regulation_id}/versions/{version_id}", response_model=RegulationVersionOut)
def get_version(regulation_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db)):
    version = db.get(RegulationVersion, version_id)
    if version is None or version.regulation_id != regulation_id:
        raise HTTPException(status_code=404, detail="Regulation version not found")
    return version


@router.post("/{regulation_id}/versions", response_model=RegulationVersionOut, status_code=201)
def create_version_endpoint(
    regulation_id: uuid.UUID, payload: RegulationVersionCreate, db: Session = Depends(get_db)
):
    regulation = db.get(Regulation, regulation_id)
    if regulation is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
    version = create_version(
        db,
        regulation,
        payload.version,
        payload.effective_from,
        payload.effective_to,
        payload.status,
        payload.source_text,
    )
    db.commit()
    db.refresh(version)
    return version


@router.get(
    "/{regulation_id}/versions/{version_id}/definitions", response_model=list[DefinitionOut]
)
def list_definitions(regulation_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db)):
    version = db.get(RegulationVersion, version_id)
    if version is None or version.regulation_id != regulation_id:
        raise HTTPException(status_code=404, detail="Regulation version not found")
    return (
        db.query(Definition)
        .filter(Definition.regulation_version_id == version_id)
        .order_by(Definition.term)
        .all()
    )


@router.get(
    "/{regulation_id}/versions/{version_id}/exceptions", response_model=list[ExceptionOut]
)
def list_exceptions(regulation_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db)):
    version = db.get(RegulationVersion, version_id)
    if version is None or version.regulation_id != regulation_id:
        raise HTTPException(status_code=404, detail="Regulation version not found")
    rule_ids = [
        r.id for r in db.query(Rule.id).filter(Rule.regulation_version_id == version_id).all()
    ]
    if not rule_ids:
        return []
    return db.query(RuleException).filter(RuleException.rule_id.in_(rule_ids)).all()


@router.post(
    "/{regulation_id}/versions/{version_id}/compile",
    response_model=CompileJobOut,
    status_code=202,
)
async def compile_version(
    regulation_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
    job_service: CompileJobService = Depends(get_compile_job_service),
):
    regulation = db.get(Regulation, regulation_id)
    if regulation is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
    version = db.get(RegulationVersion, version_id)
    if version is None or version.regulation_id != regulation_id:
        raise HTTPException(status_code=404, detail="Regulation version not found")

    job = job_service.create_job(db, regulation, version, provider_name=type(provider).__name__)
    await job_service.start(job.id, provider)
    db.refresh(job)
    return job
