import random
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User, VocabularyItem
from app.repositories import vocabulary_repo
from app.schemas.study import StudyOutcome

SESSION_SIZE = 20
MODERATE_DELAY_CHOICES = (2, 3)


def start_session(db: Session, user: User) -> tuple[int, list[VocabularyItem]]:
    user.study_session_count += 1
    db.commit()
    db.refresh(user)
    session_number = user.study_session_count

    due_words = vocabulary_repo.list_due_vocabulary(db, user.id, session_number)

    if len(due_words) > SESSION_SIZE:
        forced = random.sample(due_words, SESSION_SIZE)
        fill: list[VocabularyItem] = []
    else:
        forced = due_words
        remaining_slots = SESSION_SIZE - len(forced)
        fillable_pool = vocabulary_repo.list_fillable_vocabulary(
            db, user.id, exclude_ids={w.id for w in forced}
        )
        fill = random.sample(fillable_pool, min(remaining_slots, len(fillable_pool)))

    selected = forced + fill
    random.shuffle(selected)
    return session_number, selected


def record_review(
    db: Session, user: User, vocabulary_id: uuid.UUID, outcome: StudyOutcome
) -> VocabularyItem:
    item = vocabulary_repo.get_vocabulary(db, user.id, vocabulary_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found")

    current_session = user.study_session_count
    item.review_count += 1
    item.last_reviewed_at = datetime.now(timezone.utc)

    if outcome == "correct":
        item.correct_count += 1
        item.study_due_at_session = None
    elif outcome == "incorrect_hard":
        item.incorrect_hard_count += 1
        item.study_due_at_session = current_session + 1
    elif outcome == "incorrect_moderate":
        item.incorrect_moderate_count += 1
        item.study_due_at_session = current_session + random.choice(MODERATE_DELAY_CHOICES)

    db.commit()
    db.refresh(item)
    return item
