import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from opentelemetry import trace
from sqlalchemy.orm import Session

from app.agents.core.models import ModelHandle
from app.agents.core.runner import AIBudgetExceeded, AIRunError, run_agent
from app.agents.prompts.vocab_extraction import build_user_prompt
from app.agents.vocab import vocab_extraction_agent
from app.models import VocabExtractionJob, VocabSource, VocabularyItem
from app.models.vocabulary import ExtractionStatus, FileType
from app.parsing import docx_parser, pdf_parser, text_parser
from app.schemas.ai_outputs import ExtractedVocabEntry, VocabExtractionAIOutput
from app.schemas.vocab_extraction import VocabExtractionConfirmRequest
from app.services import deck_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Large documents are split into chunks rather than truncated, so every part of the
# document gets a chance at extraction instead of silently dropping anything past a
# fixed character limit. MAX_CHUNKS bounds total processed text (~120k chars) and
# request time on pathological uploads.
CHUNK_SIZE_CHARS = 8_000
MAX_CHUNKS = 15

_PARSERS = {
    FileType.PDF: pdf_parser.extract_text,
    FileType.DOCX: docx_parser.extract_text,
    FileType.TXT: text_parser.extract_text,
}

_EXTENSION_TO_FILE_TYPE = {
    "pdf": FileType.PDF,
    "docx": FileType.DOCX,
    "txt": FileType.TXT,
}


def resolve_file_type(filename: str) -> FileType:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    file_type = _EXTENSION_TO_FILE_TYPE.get(extension)
    if file_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Please upload a .pdf, .docx, or .txt file.",
        )
    return file_type


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS) -> list[str]:
    """Greedily pack lines into chunks up to chunk_size chars, so we never cut a line
    (e.g. a "word: translation" entry) in half."""
    lines = text.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current and current_len + line_len > chunk_size:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks[:MAX_CHUNKS]


def _dedupe_entries(entries: list[ExtractedVocabEntry]) -> list[ExtractedVocabEntry]:
    seen: set[tuple[str, str]] = set()
    unique: list[ExtractedVocabEntry] = []
    for entry in entries:
        key = (entry.word.strip().lower(), entry.part_of_speech.value)
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
    return unique


def run_extraction(
    db: Session,
    model: ModelHandle,
    user_id: uuid.UUID,
    filename: str,
    file_bytes: bytes,
    max_retries: int,
) -> VocabExtractionJob:
    file_type = resolve_file_type(filename)
    job = VocabExtractionJob(
        user_id=user_id,
        original_filename=filename,
        file_type=file_type,
        status=ExtractionStatus.PROCESSING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # One parent span per job, so every chunk's agent run lands in the same trace.
    with tracer.start_as_current_span("vocab_extraction_job") as span:
        span.set_attribute("app.job_id", str(job.id))
        try:
            source_text = _PARSERS[file_type](file_bytes)
            if not source_text.strip():
                raise ValueError("No extractable text found in the uploaded file.")

            chunks = _chunk_text(source_text)
            all_entries: list[ExtractedVocabEntry] = []
            chunk_errors: list[str] = []

            for i, chunk in enumerate(chunks):
                try:
                    result = run_agent(
                        db,
                        vocab_extraction_agent,
                        build_user_prompt(chunk),
                        feature="vocab_extraction",
                        model=model,
                        user_id=user_id,
                        max_retries=max_retries,
                    )
                    all_entries.extend(result.entries)
                except AIBudgetExceeded as exc:
                    # No point trying the remaining chunks; keep whatever was extracted so far.
                    chunk_errors.append(str(exc))
                    break
                except AIRunError as exc:  # one bad chunk shouldn't sink the whole job
                    logger.warning("Chunk %d/%d failed to extract: %s", i + 1, len(chunks), exc)
                    chunk_errors.append(str(exc))

            if not all_entries and chunk_errors:
                raise AIRunError("; ".join(chunk_errors[:3]))

            unique_entries = _dedupe_entries(all_entries)
            job.status = ExtractionStatus.COMPLETED
            job.raw_ai_output = VocabExtractionAIOutput(entries=unique_entries).model_dump(mode="json")
            if chunk_errors:
                job.error_message = (
                    f"{len(chunk_errors)} of {len(chunks)} chunk(s) failed to extract; "
                    "showing results from the rest."
                )
        except (AIRunError, ValueError) as exc:
            job.status = ExtractionStatus.FAILED
            job.error_message = str(exc)
        except Exception as exc:  # noqa: BLE001 - e.g. a corrupt file the parser chokes on
            logger.exception("Vocab extraction failed for job %s", job.id)
            job.status = ExtractionStatus.FAILED
            job.error_message = f"Extraction failed: {exc}"

    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


def get_job_or_404(
    db: Session, user_id: uuid.UUID, job_id: uuid.UUID, lock: bool = False
) -> VocabExtractionJob:
    job = db.get(VocabExtractionJob, job_id, with_for_update=lock)
    if job is None or job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction job not found")
    return job


def confirm_extraction(
    db: Session, user_id: uuid.UUID, job_id: uuid.UUID, payload: VocabExtractionConfirmRequest
) -> list[VocabularyItem]:
    # Row lock so two concurrent confirms (e.g. a double click) can't both pass the check below.
    job = get_job_or_404(db, user_id, job_id, lock=True)
    if job.status != ExtractionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed extraction jobs can be confirmed.",
        )
    if job.confirmed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This extraction job has already been confirmed.",
        )
    if payload.deck_id is not None:
        deck_service.get_deck_or_404(db, user_id, payload.deck_id)

    created_items = []
    for entry in payload.entries:
        item = VocabularyItem(
            user_id=user_id,
            deck_id=payload.deck_id,
            source=VocabSource.AI_EXTRACTED,
            source_file_name=job.original_filename,
            **entry.model_dump(),
        )
        db.add(item)
        created_items.append(item)

    job.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    for item in created_items:
        db.refresh(item)
    return created_items
