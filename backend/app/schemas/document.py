from pydantic import BaseModel


class DocumentExtractionOut(BaseModel):
    filename: str
    text: str
    character_count: int
