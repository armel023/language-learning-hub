import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.config import Settings, get_settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.vocab_extraction import VocabExtractionConfirmRequest, VocabExtractionJobRead
from app.schemas.vocabulary import VocabularyItemRead
from app.services import vocab_extraction_service

router = APIRouter(prefix="/vocab-extraction", tags=["vocab-extraction"])


@router.post("/upload", response_model=VocabExtractionJobRead)
async def upload_file(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_provider: AIProvider = Depends(get_ai_provider),
    settings: Settings = Depends(get_settings),
) -> VocabExtractionJobRead:
    file_bytes = await file.read()
    job = vocab_extraction_service.run_extraction(
        db,
        ai_provider,
        current_user.id,
        file.filename or "upload",
        file_bytes,
        settings.ai_json_max_retries,
    )
    return VocabExtractionJobRead.model_validate(job)


@router.get("/{job_id}", response_model=VocabExtractionJobRead)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VocabExtractionJobRead:
    job = vocab_extraction_service.get_job_or_404(db, current_user.id, job_id)
    return VocabExtractionJobRead.model_validate(job)


@router.post("/{job_id}/confirm", response_model=list[VocabularyItemRead])
def confirm_job(
    job_id: uuid.UUID,
    payload: VocabExtractionConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[VocabularyItemRead]:
    items = vocab_extraction_service.confirm_extraction(db, current_user.id, job_id, payload)
    return [VocabularyItemRead.model_validate(item) for item in items]
