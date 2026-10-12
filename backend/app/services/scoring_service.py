from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Attempt, AttemptStatus, Exercise, User
from app.repositories import attempt_repo


def score_attempt(
    db: Session, user: User, exercise: Exercise, answers: dict[str, int | str]
) -> Attempt:
    """Instant scoring for skills with an objective answer key (Lesen, later Hören)."""
    if exercise.answer_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This exercise has no answer key; it is graded by rubric instead.",
        )
    correct_answers: dict[str, int | str] = exercise.answer_key.get("answers", {})

    if set(answers.keys()) != set(correct_answers.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected an answer for each question: {sorted(correct_answers.keys())}",
        )

    is_correct_per_question = {
        qnum: answers[qnum] == correct_answers[qnum] for qnum in correct_answers
    }
    score = sum(is_correct_per_question.values())

    attempt = Attempt(
        user_id=user.id,
        exercise_id=exercise.id,
        status=AttemptStatus.GRADED,
        submitted_at=datetime.now(timezone.utc),
        score=score,
        max_score=len(correct_answers),
        answers={"answers": answers},
        is_correct_per_question=is_correct_per_question,
    )
    return attempt_repo.create_attempt(db, attempt)
