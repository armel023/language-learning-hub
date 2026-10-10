import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agents import lesen
from app.agents.core.models import ModelHandle
from app.agents.core.runner import AIBudgetExceeded, AIRunError, run_agent
from app.agents.prompts import reading_teil1, reading_teil2, reading_teil3, reading_teil4
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
    db: Session,
    model: ModelHandle,
    user_id: uuid.UUID,
    payload: ReadingExerciseGenerateRequest,
    max_retries: int,
) -> ReadingExercise:
    ctx = _GenerationContext(db, model, user_id, max_retries)
    if payload.teil == 1:
        return _generate_teil1(ctx, payload)
    if payload.teil == 2:
        return _generate_teil2(ctx, payload)
    if payload.teil == 3:
        return _generate_teil3(ctx, payload)
    if payload.teil == 4:
        return _generate_teil4(ctx, payload)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Lesen Teil {payload.teil} is coming soon.",
    )


@dataclass(frozen=True)
class _GenerationContext:
    db: Session
    model: ModelHandle
    user_id: uuid.UUID
    max_retries: int


def _run_ai_generation(ctx: _GenerationContext, agent, user_prompt: str, feature: str):
    try:
        return run_agent(
            ctx.db,
            agent,
            user_prompt,
            feature=feature,
            model=ctx.model,
            user_id=ctx.user_id,
            max_retries=ctx.max_retries,
        )
    except AIBudgetExceeded as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except AIRunError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI generation failed: {exc}"
        ) from exc


def _generated_by(model: ModelHandle) -> GeneratedBy:
    return GeneratedBy.AI_OLLAMA if model.provider == "ollama" else GeneratedBy.AI_GEMINI


def _generate_teil1(ctx: _GenerationContext, payload: ReadingExerciseGenerateRequest) -> ReadingExercise:
    user_prompt = reading_teil1.build_user_prompt(payload.topic, payload.level)
    ai_output: ReadingTeil1AIOutput = _run_ai_generation(ctx, lesen.teil1_agent, user_prompt, "lesen_teil1")
    content, answer_key = _split_teil1_output(ai_output)

    exercise = ReadingExercise(
        exercise_type=ExerciseType.LESEN_TEIL1,
        title=ai_output.article_title,
        level=payload.level,
        topic=payload.topic,
        content=content,
        answer_key=answer_key,
        generated_by=_generated_by(ctx.model),
        generation_prompt=user_prompt,
    )
    return reading_repo.create_exercise(ctx.db, exercise)


def _generate_teil2(ctx: _GenerationContext, payload: ReadingExerciseGenerateRequest) -> ReadingExercise:
    user_prompt = reading_teil2.build_user_prompt(payload.topic, payload.level)
    ai_output: ReadingTeil2AIOutput = _run_ai_generation(ctx, lesen.teil2_agent, user_prompt, "lesen_teil2")
    content, answer_key = _split_teil2_output(ai_output)

    title = f"Im Kaufhaus: {payload.topic}" if payload.topic else "Im Kaufhaus"
    exercise = ReadingExercise(
        exercise_type=ExerciseType.LESEN_TEIL2,
        title=title,
        level=payload.level,
        topic=payload.topic,
        content=content,
        answer_key=answer_key,
        generated_by=_generated_by(ctx.model),
        generation_prompt=user_prompt,
    )
    return reading_repo.create_exercise(ctx.db, exercise)


def _generate_teil3(ctx: _GenerationContext, payload: ReadingExerciseGenerateRequest) -> ReadingExercise:
    user_prompt = reading_teil3.build_user_prompt(payload.topic, payload.level)
    ai_output: ReadingTeil3AIOutput = _run_ai_generation(ctx, lesen.teil3_agent, user_prompt, "lesen_teil3")
    content, answer_key = _split_teil3_output(ai_output)

    exercise = ReadingExercise(
        exercise_type=ExerciseType.LESEN_TEIL3,
        title=ai_output.email_subject,
        level=payload.level,
        topic=payload.topic,
        content=content,
        answer_key=answer_key,
        generated_by=_generated_by(ctx.model),
        generation_prompt=user_prompt,
    )
    return reading_repo.create_exercise(ctx.db, exercise)


def _generate_teil4(ctx: _GenerationContext, payload: ReadingExerciseGenerateRequest) -> ReadingExercise:
    user_prompt = reading_teil4.build_user_prompt(payload.topic, payload.level)
    ai_output: ReadingTeil4AIOutput = _run_ai_generation(ctx, lesen.teil4_agent, user_prompt, "lesen_teil4")
    content, answer_key = _split_teil4_output(ai_output)

    title = f"Anzeigen: {payload.topic}" if payload.topic else "Anzeigen"
    exercise = ReadingExercise(
        exercise_type=ExerciseType.LESEN_TEIL4,
        title=title,
        level=payload.level,
        topic=payload.topic,
        content=content,
        answer_key=answer_key,
        generated_by=_generated_by(ctx.model),
        generation_prompt=user_prompt,
    )
    return reading_repo.create_exercise(ctx.db, exercise)


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
