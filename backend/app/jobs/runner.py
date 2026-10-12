"""Minimal in-process background job runner.

Agent runs can take tens of seconds (generator + verifier loops, many vocab chunks, grading),
so endpoints enqueue a Job and return its id; the client polls GET /jobs/{id}.

Deliberately small: a thread pool inside the API process. The public surface is `job_handler`,
`enqueue` and `fail_interrupted_jobs`, so moving to a real queue (arq + Redis) later only
replaces this module. Until then, run the API as a single process: on startup every job that
was still pending/running is marked failed, which would be wrong with several workers.
"""
import logging
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from opentelemetry import trace
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import SessionLocal
from app.models import ExtractionStatus, Job, JobStatus, VocabExtractionJob
from app.repositories import job_repo

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

JobHandler = Callable[[Session, Job], dict | None]

_handlers: dict[str, JobHandler] = {}
_executor: ThreadPoolExecutor | None = None

# Swappable in tests; each job runs in its own session, never the request's.
session_factory: Callable[[], Session] = SessionLocal


class JobFailed(Exception):
    """Raise from a handler for an expected failure the user should see (budget, AI error).

    Anything the handler wants persisted alongside the failure must be committed before
    raising, because the runner rolls the session back.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def job_handler(kind: str) -> Callable[[JobHandler], JobHandler]:
    def register(fn: JobHandler) -> JobHandler:
        if kind in _handlers:
            raise RuntimeError(f"Duplicate job handler for {kind!r}")
        _handlers[kind] = fn
        return fn

    return register


def enqueue(db: Session, kind: str, *, user_id: uuid.UUID | None, input: dict) -> Job:
    if kind not in _handlers:
        raise ValueError(f"No job handler registered for {kind!r}")
    job = job_repo.create_job(db, Job(kind=kind, user_id=user_id, input=input, status=JobStatus.PENDING))

    if get_settings().jobs_run_inline:
        execute_job(job.id)
        db.refresh(job)
    else:
        _get_executor().submit(execute_job, job.id)
    return job


def execute_job(job_id: uuid.UUID) -> None:
    db = session_factory()
    try:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("Job %s vanished before it could run", job_id)
            return
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        kind = job.kind
        try:
            with tracer.start_as_current_span(f"job {kind}") as span:
                span.set_attribute("app.job_id", str(job_id))
                result = _handlers[kind](db, job)
        except JobFailed as exc:
            _finish_failed(db, job_id, exc.code, exc.message)
            return
        except Exception as exc:  # noqa: BLE001 - a crashing handler must still leave the job in a final state
            logger.exception("Job %s (%s) crashed", job_id, kind)
            _finish_failed(db, job_id, "internal_error", f"Unexpected error: {exc}")
            return

        job.status = JobStatus.SUCCEEDED
        job.result = result
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def fail_interrupted_jobs(db: Session) -> None:
    """Called on startup: anything still pending/running died with the previous process."""
    message = "The server restarted before this job finished. Please try again."
    count = job_repo.fail_unfinished_jobs(db, message)
    vocab = db.execute(
        update(VocabExtractionJob)
        .where(VocabExtractionJob.status.in_([ExtractionStatus.PENDING, ExtractionStatus.PROCESSING]))
        .values(status=ExtractionStatus.FAILED, error_message=message, completed_at=datetime.now(timezone.utc))
    ).rowcount
    db.commit()
    if count or vocab:
        logger.warning("Marked %d job(s) and %d vocab extraction(s) as interrupted", count, vocab)


def _finish_failed(db: Session, job_id: uuid.UUID, code: str, message: str) -> None:
    db.rollback()
    job = db.get(Job, job_id)
    job.status = JobStatus.FAILED
    job.error_code = code
    job.error_message = message
    job.finished_at = datetime.now(timezone.utc)
    db.commit()


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=get_settings().jobs_max_workers, thread_name_prefix="job")
    return _executor
