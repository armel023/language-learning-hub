import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.json_validation import AIGenerationError, generate_validated
from app.ai.prompts import reading_teil1, reading_teil2, reading_teil3, reading_teil4
from app.config import get_settings
from app.models import GeneratedBy, ReadingExercise
from app.models.reading_exercise import ExerciseType
from app.repositories import reading_repo
from app.schemas.ai_outputs import (
    ReadingTeil1AIOutput,
    ReadingTeil2AIOutput,
    ReadingTeil3AIOutput,
    ReadingTeil4AIOutput,
)
from app.schemas.reading import ReadingExerciseGenerateRequest

_TEIL_TO_TYPE = {
    1: ExerciseType.LESEN_TEIL1,
    2: ExerciseType.LESEN_TEIL2,
    3: ExerciseType.LESEN_TEIL3,
    4: ExerciseType.LESEN_TEIL4,
}


def list_exercises(db: Session, teil: int | None) -> list[ReadingExercise]:
    exercise_type = _TEIL_TO_TYPE.get(teil) if teil is not None else None
    return reading_repo.list_exercises(db, exercise_type)


def get_exercise_or_404(db: Session, exercise_id: uuid.UUID) -> ReadingExercise:
    exercise = reading_repo.get_exercise(db, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading exercise not found")
    return exercise


def generate_exercise(
    db: Session, ai_provider: AIProvider, payload: ReadingExerciseGenerateRequest, max_retries: int
) -> ReadingExercise:
    if payload.teil == 1:
        return _generate_teil1(db, ai_provider, payload, max_retries)
    if payload.teil == 2:
        return _generate_teil2(db, ai_provider, payload, max_retries)
    if payload.teil == 3:
        return _generate_teil3(db, ai_provider, payload, max_retries)
    if payload.teil == 4:
        return _generate_teil4(db, ai_provider, payload, max_retries)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Lesen Teil {payload.teil} is coming soon.",
    )


def _run_ai_generation(ai_provider, system_prompt, user_prompt, schema, max_retries):
    try:
        return generate_validated(ai_provider, system_prompt, user_prompt, schema, max_retries=max_retries)
    except AIGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI generation failed: {exc}"
        ) from exc


def _generated_by() -> GeneratedBy:
    return GeneratedBy.AI_OLLAMA if get_settings().ai_provider == "ollama" else GeneratedBy.AI_GEMINI


def _generate_teil1(
    db: Session, ai_provider: AIProvider, payload: ReadingExerciseGenerateRequest, max_retries: int
) -> ReadingExercise:
    user_prompt = reading_teil1.build_user_prompt(payload.topic, payload.level)
    ai_output = _run_ai_generation(
        ai_provider, reading_teil1.SYSTEM_PROMPT, user_prompt, ReadingTeil1AIOutput, max_retries
    )
    content, answer_key = _split_teil1_output(ai_output)

    exercise = ReadingExercise(
        exercise_type=ExerciseType.LESEN_TEIL1,
        title=ai_output.article_title,
        level=payload.level,
        topic=payload.topic,
        content=content,
        answer_key=answer_key,
        generated_by=_generated_by(),
        generation_prompt=user_prompt,
    )
    return reading_repo.create_exercise(db, exercise)


def _generate_teil2(
    db: Session, ai_provider: AIProvider, payload: ReadingExerciseGenerateRequest, max_retries: int
) -> ReadingExercise:
    user_prompt = reading_teil2.build_user_prompt(payload.topic, payload.level)
    ai_output = _run_ai_generation(
        ai_provider, reading_teil2.SYSTEM_PROMPT, user_prompt, ReadingTeil2AIOutput, max_retries
    )
    content, answer_key = _split_teil2_output(ai_output)

    title = f"Im Kaufhaus: {payload.topic}" if payload.topic else "Im Kaufhaus"
    exercise = ReadingExercise(
        exercise_type=ExerciseType.LESEN_TEIL2,
        title=title,
        level=payload.level,
        topic=payload.topic,
        content=content,
        answer_key=answer_key,
        generated_by=_generated_by(),
        generation_prompt=user_prompt,
    )
    return reading_repo.create_exercise(db, exercise)


def _generate_teil3(
    db: Session, ai_provider: AIProvider, payload: ReadingExerciseGenerateRequest, max_retries: int
) -> ReadingExercise:
    user_prompt = reading_teil3.build_user_prompt(payload.topic, payload.level)
    ai_output = _run_ai_generation(
        ai_provider, reading_teil3.SYSTEM_PROMPT, user_prompt, ReadingTeil3AIOutput, max_retries
    )
    content, answer_key = _split_teil3_output(ai_output)

    exercise = ReadingExercise(
        exercise_type=ExerciseType.LESEN_TEIL3,
        title=ai_output.email_subject,
        level=payload.level,
        topic=payload.topic,
        content=content,
        answer_key=answer_key,
        generated_by=_generated_by(),
        generation_prompt=user_prompt,
    )
    return reading_repo.create_exercise(db, exercise)


def _generate_teil4(
    db: Session, ai_provider: AIProvider, payload: ReadingExerciseGenerateRequest, max_retries: int
) -> ReadingExercise:
    user_prompt = reading_teil4.build_user_prompt(payload.topic, payload.level)
    ai_output = _run_ai_generation(
        ai_provider, reading_teil4.SYSTEM_PROMPT, user_prompt, ReadingTeil4AIOutput, max_retries
    )
    content, answer_key = _split_teil4_output(ai_output)

    title = f"Anzeigen: {payload.topic}" if payload.topic else "Anzeigen"
    exercise = ReadingExercise(
        exercise_type=ExerciseType.LESEN_TEIL4,
        title=title,
        level=payload.level,
        topic=payload.topic,
        content=content,
        answer_key=answer_key,
        generated_by=_generated_by(),
        generation_prompt=user_prompt,
    )
    return reading_repo.create_exercise(db, exercise)


def _split_teil1_output(ai_output: ReadingTeil1AIOutput) -> tuple[dict, dict]:
    content = {
        "article_title": ai_output.article_title,
        "beispiel": ai_output.beispiel.model_dump(),
        "paragraphs": [p.model_dump() for p in ai_output.paragraphs],
        "questions": [
            {
                "question_number": q.question_number,
                "paragraph_number": q.paragraph_number,
                "prompt": q.prompt,
                "options": q.options,
            }
            for q in ai_output.questions
        ],
    }
    answer_key = {
        "answers": {str(q.question_number): q.correct_option_index for q in ai_output.questions},
        "explanations": {str(q.question_number): q.explanation for q in ai_output.questions},
    }
    return content, answer_key


def _split_teil4_output(ai_output: ReadingTeil4AIOutput) -> tuple[dict, dict]:
    content = {
        "ads": [ad.model_dump() for ad in ai_output.ads],
        "beispiel": {
            "prompt": ai_output.beispiel.prompt,
            "correct_ad_code": ai_output.beispiel.correct_ad_code,
            "explanation": ai_output.beispiel.explanation,
        },
        "aufgaben": [
            {"aufgabe_number": a.aufgabe_number, "prompt": a.prompt} for a in ai_output.aufgaben
        ],
    }
    answer_key = {
        "answers": {str(a.aufgabe_number): a.correct_ad_code for a in ai_output.aufgaben},
        "explanations": {str(a.aufgabe_number): a.explanation for a in ai_output.aufgaben},
    }
    return content, answer_key


def _split_teil2_output(ai_output: ReadingTeil2AIOutput) -> tuple[dict, dict]:
    def build_options(option_a: str, option_b: str) -> list[str]:
        return [option_a, option_b, "Anderer Stock"]

    content = {
        "groups": [g.model_dump() for g in ai_output.groups],
        "beispiel": {
            "prompt": ai_output.beispiel.prompt,
            "options": build_options(ai_output.beispiel.option_a, ai_output.beispiel.option_b),
            "correct_option_index": ai_output.beispiel.correct_option_index,
            "explanation": ai_output.beispiel.explanation,
        },
        "aufgaben": [
            {
                "aufgabe_number": a.aufgabe_number,
                "prompt": a.prompt,
                "options": build_options(a.option_a, a.option_b),
            }
            for a in ai_output.aufgaben
        ],
    }
    answer_key = {
        "answers": {str(a.aufgabe_number): a.correct_option_index for a in ai_output.aufgaben},
        "explanations": {str(a.aufgabe_number): a.explanation for a in ai_output.aufgaben},
    }
    return content, answer_key


def _split_teil3_output(ai_output: ReadingTeil3AIOutput) -> tuple[dict, dict]:
    content = {
        "email_subject": ai_output.email_subject,
        "email_sender_name": ai_output.email_sender_name,
        "greeting": ai_output.greeting,
        "closing_phrase": ai_output.closing_phrase,
        "beispiel": ai_output.beispiel.model_dump(),
        "paragraphs": [p.model_dump() for p in ai_output.paragraphs],
        "questions": [
            {
                "question_number": q.question_number,
                "paragraph_number": q.paragraph_number,
                "prompt": q.prompt,
                "options": q.options,
            }
            for q in ai_output.questions
        ],
    }
    answer_key = {
        "answers": {str(q.question_number): q.correct_option_index for q in ai_output.questions},
        "explanations": {str(q.question_number): q.explanation for q in ai_output.questions},
    }
    return content, answer_key
