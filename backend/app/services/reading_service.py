import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agents import lesen
from app.agents.core import models as agent_models
from app.agents.core.models import ModelHandle
from app.agents.core.runner import AIBudgetExceeded, AIRunError, run_agent
from app.agents.prompts import reading_teil1, reading_teil2, reading_teil3, reading_teil4
from app.config import get_settings
from app.jobs.runner import JobFailed, enqueue, job_handler
from app.models import Exercise, GeneratedBy, Job, Skill
from app.repositories import exercise_repo
from app.schemas.ai_outputs import (
    ReadingTeil1AIOutput,
    ReadingTeil2AIOutput,
    ReadingTeil3AIOutput,
    ReadingTeil4AIOutput,
)
from app.schemas.reading import ReadingExerciseGenerateRequest

GENERATE_JOB = "lesen_generate"


def list_exercises(db: Session, teil: int | None) -> list[Exercise]:
    return exercise_repo.list_exercises(db, Skill.LESEN, teil)


def get_exercise_or_404(db: Session, exercise_id: uuid.UUID) -> Exercise:
    exercise = exercise_repo.get_exercise(db, exercise_id)
    if exercise is None or exercise.skill != Skill.LESEN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading exercise not found")
    return exercise


def start_generation(db: Session, user_id: uuid.UUID, payload: ReadingExerciseGenerateRequest) -> Job:
    """Queue exercise generation; the job's result is {"exercise_id": ...} once it succeeds."""
    return enqueue(db, GENERATE_JOB, user_id=user_id, input=payload.model_dump())


@job_handler(GENERATE_JOB)
def _generation_job(db: Session, job: Job) -> dict:
    payload = ReadingExerciseGenerateRequest.model_validate(job.input)
    try:
        exercise = generate_exercise(
            db, agent_models.get_model(), job.user_id, payload, get_settings().ai_json_max_retries
        )
    except AIBudgetExceeded as exc:
        raise JobFailed("budget_exceeded", str(exc)) from exc
    except AIRunError as exc:
        raise JobFailed("ai_failed", f"AI generation failed: {exc}") from exc
    return {"exercise_id": str(exercise.id)}


def generate_exercise(
    db: Session,
    model: ModelHandle,
    user_id: uuid.UUID | None,
    payload: ReadingExerciseGenerateRequest,
    max_retries: int,
) -> Exercise:
    ctx = _GenerationContext(db, model, user_id, max_retries)
    generators = {1: _generate_teil1, 2: _generate_teil2, 3: _generate_teil3, 4: _generate_teil4}
    return generators[payload.teil](ctx, payload)


@dataclass(frozen=True)
class _GenerationContext:
    db: Session
    model: ModelHandle
    user_id: uuid.UUID | None
    max_retries: int


def _run_ai_generation(ctx: _GenerationContext, agent, user_prompt: str, feature: str):
    return run_agent(
        ctx.db,
        agent,
        user_prompt,
        feature=feature,
        model=ctx.model,
        user_id=ctx.user_id,
        max_retries=ctx.max_retries,
    )


def _generated_by(model: ModelHandle) -> GeneratedBy:
    return GeneratedBy.AI_OLLAMA if model.provider == "ollama" else GeneratedBy.AI_GEMINI


def _save(ctx: _GenerationContext, payload: ReadingExerciseGenerateRequest, title: str,
          content: dict, answer_key: dict, user_prompt: str) -> Exercise:
    exercise = Exercise(
        skill=Skill.LESEN,
        teil=payload.teil,
        title=title,
        level=payload.level,
        topic=payload.topic,
        content=content,
        answer_key=answer_key,
        generated_by=_generated_by(ctx.model),
        generation_prompt=user_prompt,
        user_id=ctx.user_id,
    )
    return exercise_repo.create_exercise(ctx.db, exercise)


def _generate_teil1(ctx: _GenerationContext, payload: ReadingExerciseGenerateRequest) -> Exercise:
    user_prompt = reading_teil1.build_user_prompt(payload.topic, payload.level)
    ai_output: ReadingTeil1AIOutput = _run_ai_generation(ctx, lesen.teil1_agent, user_prompt, "lesen_teil1")
    content, answer_key = _split_teil1_output(ai_output)
    return _save(ctx, payload, ai_output.article_title, content, answer_key, user_prompt)


def _generate_teil2(ctx: _GenerationContext, payload: ReadingExerciseGenerateRequest) -> Exercise:
    user_prompt = reading_teil2.build_user_prompt(payload.topic, payload.level)
    ai_output: ReadingTeil2AIOutput = _run_ai_generation(ctx, lesen.teil2_agent, user_prompt, "lesen_teil2")
    content, answer_key = _split_teil2_output(ai_output)
    title = f"Im Kaufhaus: {payload.topic}" if payload.topic else "Im Kaufhaus"
    return _save(ctx, payload, title, content, answer_key, user_prompt)


def _generate_teil3(ctx: _GenerationContext, payload: ReadingExerciseGenerateRequest) -> Exercise:
    user_prompt = reading_teil3.build_user_prompt(payload.topic, payload.level)
    ai_output: ReadingTeil3AIOutput = _run_ai_generation(ctx, lesen.teil3_agent, user_prompt, "lesen_teil3")
    content, answer_key = _split_teil3_output(ai_output)
    return _save(ctx, payload, ai_output.email_subject, content, answer_key, user_prompt)


def _generate_teil4(ctx: _GenerationContext, payload: ReadingExerciseGenerateRequest) -> Exercise:
    user_prompt = reading_teil4.build_user_prompt(payload.topic, payload.level)
    ai_output: ReadingTeil4AIOutput = _run_ai_generation(ctx, lesen.teil4_agent, user_prompt, "lesen_teil4")
    content, answer_key = _split_teil4_output(ai_output)
    title = f"Anzeigen: {payload.topic}" if payload.topic else "Anzeigen"
    return _save(ctx, payload, title, content, answer_key, user_prompt)


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
