import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Job, JobStatus


def create_job(db: Session, job: Job) -> Job:
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, user_id: uuid.UUID, job_id: uuid.UUID) -> Job | None:
    stmt = select(Job).where(Job.id == job_id, Job.user_id == user_id)
    return db.scalars(stmt).first()


def fail_unfinished_jobs(db: Session, message: str) -> int:
    result = db.execute(
        update(Job)
        .where(Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]))
        .values(
            status=JobStatus.FAILED,
            error_code="interrupted",
            error_message=message,
            finished_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return result.rowcount
