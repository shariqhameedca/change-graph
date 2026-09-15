from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.document import DocumentExtractionOut
from app.services.document_service import DocumentExtractionError, extract_text_from_upload

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/extract-text", response_model=DocumentExtractionOut)
async def extract_text(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = extract_text_from_upload(file.filename or "upload.txt", content)
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return DocumentExtractionOut(
        filename=file.filename or "upload.txt", text=text, character_count=len(text)
    )
