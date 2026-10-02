from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import ReadingAttempt, ReadingExercise, User
from app.repositories import attempt_repo


def score_attempt(
    db: Session, user: User, exercise: ReadingExercise, answers: dict[str, int | str]
) -> ReadingAttempt:
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

    attempt = ReadingAttempt(
        user_id=user.id,
        reading_exercise_id=exercise.id,
        submitted_at=datetime.now(timezone.utc),
        score=score,
        max_score=len(correct_answers),
        answers={"answers": answers},
        is_correct_per_question=is_correct_per_question,
    )
    return attempt_repo.create_attempt(db, attempt)
