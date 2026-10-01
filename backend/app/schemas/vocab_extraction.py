import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.vocabulary import ExtractionStatus, FileType
from app.schemas.ai_outputs import ExtractedVocabEntry


class VocabExtractionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_type: FileType
    status: ExtractionStatus
    raw_ai_output: dict | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class VocabExtractionConfirmRequest(BaseModel):
    entries: list[ExtractedVocabEntry]
    deck_id: uuid.UUID | None = None
