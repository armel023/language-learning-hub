import logging
import time
import uuid

from fastapi import HTTPException, status
from opentelemetry import trace
from sqlalchemy.orm import Session

from app.agents import hoeren
from app.agents.core import models as agent_models
from app.agents.core.checked import RunContext, UnverifiedExercise, generate_checked
from app.agents.core.models import ModelHandle
from app.agents.core.runner import AIBudgetExceeded, AIRunError
from app.audio import storage
from app.audio.mixing import Line, render_script
from app.audio.tts import TTSEngine, get_tts_engine
from app.config import get_settings
from app.jobs.runner import JobFailed, enqueue, job_handler
from app.models import AIRun, AIRunStatus, Exercise, GeneratedBy, Job, PartOfSpeech, Skill, User
from app.repositories import ai_run_repo, exercise_repo, vocabulary_repo
from app.schemas.hoeren import HoerenAttemptResult, HoerenGenerateRequest
from app.schemas.reading import ReadingAttemptSubmit
from app.services import scoring_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

GENERATE_JOB = "hoeren_generate"


def list_exercises(db: Session, teil: int | None) -> list[Exercise]:
    return exercise_repo.list_exercises(db, Skill.HOEREN, teil)


def get_exercise_or_404(db: Session, exercise_id: uuid.UUID) -> Exercise:
    exercise = exercise_repo.get_exercise(db, exercise_id)
    if exercise is None or exercise.skill != Skill.HOEREN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hören exercise not found")
    return exercise


# --- generation --------------------------------------------------------------------------


def start_generation(db: Session, user_id: uuid.UUID, payload: HoerenGenerateRequest) -> Job:
    return enqueue(db, GENERATE_JOB, user_id=user_id, input=payload.model_dump())


@job_handler(GENERATE_JOB)
def _generation_job(db: Session, job: Job) -> dict:
    payload = HoerenGenerateRequest.model_validate(job.input)
    try:
        exercise = generate_exercise(db, agent_models.get_model(), get_tts_engine(), job.user_id, payload)
    except AIBudgetExceeded as exc:
        raise JobFailed("budget_exceeded", str(exc)) from exc
    except UnverifiedExercise as exc:
        raise JobFailed(
            "unverified",
            "The AI could not produce an exercise whose answers an independent check agreed with. Please try again.",
        ) from exc
    except AIRunError as exc:
        raise JobFailed("ai_failed", f"AI generation failed: {exc}") from exc
    except AudioGenerationError as exc:
        raise JobFailed("tts_failed", f"Creating the audio failed: {exc}") from exc
    return {"exercise_id": str(exercise.id)}


class AudioGenerationError(Exception):
    pass


def generate_exercise(
    db: Session, model: ModelHandle, engine: TTSEngine, user_id: uuid.UUID | None, payload: HoerenGenerateRequest
) -> Exercise:
    """Script first (generated and checked from the transcript), audio second: no TTS time or cost
    is spent on a script the checker rejected."""
    settings = get_settings()
    spec = hoeren.SPECS[payload.teil]
    result = generate_checked(
        RunContext(db, model, user_id, settings.ai_json_max_retries),
        spec,
        payload.topic,
        payload.level,
        max_revisions=settings.exercise_max_revisions,
        require_verification=settings.exercise_require_verification,
    )

    exercise_id = uuid.uuid4()
    media_dir = f"hoeren/{exercise_id}"
    try:
        audio = _render_audio(db, engine, user_id, media_dir, hoeren.scripts(result.output))
    except Exception as exc:
        storage.delete_dir(media_dir)
        logger.exception("TTS failed for Hören Teil %s", payload.teil)
        raise AudioGenerationError(str(exc)) from exc

    content = _attach_audio(result.content, audio, payload.teil)
    exercise = Exercise(
        id=exercise_id,
        skill=Skill.HOEREN,
        teil=payload.teil,
        title=spec.title(result.output, payload.topic),
        level=payload.level,
        topic=payload.topic,
        content=content,
        answer_key=result.answer_key,
        media={"audio": audio, "tts": engine.name},
        generated_by=GeneratedBy.AI_OLLAMA if model.provider == "ollama" else GeneratedBy.AI_GEMINI,
        generation_prompt=spec.build_prompt(payload.topic, payload.level),
        generation_meta=result.meta(),
        user_id=user_id,
    )
    try:
        return exercise_repo.create_exercise(db, exercise)
    except Exception:
        storage.delete_dir(media_dir)
        raise


def _render_audio(db, engine: TTSEngine, user_id, media_dir: str, segments: dict) -> dict[str, dict]:
    audio: dict[str, dict] = {}
    started = time.perf_counter()
    tokens = 0
    with tracer.start_as_current_span("hoeren_tts") as span:
        span.set_attribute("app.tts_engine", engine.name)
        span.set_attribute("app.segments", len(segments))
        try:
            for key, script in segments.items():
                rendered = render_script([Line(s.speaker, s.gender, s.text) for s in script], engine)
                url = storage.save(f"{media_dir}/{key}.wav", rendered.wav)
                audio[key] = {"url": url, "duration_s": rendered.duration_s}
                tokens += rendered.tokens
        finally:
            # One ai_runs row per exercise's audio, so TTS time (and Gemini TTS tokens) show up
            # next to the text agents in usage and budgets.
            ai_run_repo.create_run(db, AIRun(
                user_id=user_id, feature="hoeren_tts", provider=engine.name,
                model_name=get_settings().gemini_tts_model if engine.name == "gemini" else "piper",
                status=AIRunStatus.SUCCEEDED if len(audio) == len(segments) else AIRunStatus.FAILED,
                requests=len(audio), total_tokens=tokens, output_tokens=tokens,
                latency_ms=int((time.perf_counter() - started) * 1000),
            ))
    return audio


def _attach_audio(content: dict, audio: dict[str, dict], teil: int) -> dict:
    content = {**content, "plays": hoeren.PLAYS[teil]}
    if "items" in content:  # Teil 1 and 3: one clip per item
        content["items"] = [{**item, "audio": audio[str(item["item_number"])]} for item in content["items"]]
    else:  # Teil 2 and 4: one clip for the whole Teil
        content["audio"] = audio["all"]
    return content


# --- attempts ----------------------------------------------------------------------------


def submit_attempt(db: Session, user: User, payload: ReadingAttemptSubmit) -> HoerenAttemptResult:
    exercise = get_exercise_or_404(db, payload.exercise_id)
    attempt = scoring_service.score_attempt(db, user, exercise, payload.answers)
    key = exercise.answer_key
    vocabulary = key.get("vocabulary", [])
    existing = vocabulary_repo.existing_word_keys(
        db, user.id, {(v["word"].strip().lower(), PartOfSpeech(v["part_of_speech"])) for v in vocabulary}
    )
    return HoerenAttemptResult(
        id=attempt.id,
        exercise_id=exercise.id,
        score=attempt.score,
        max_score=attempt.max_score,
        is_correct_per_question=attempt.is_correct_per_question,
        correct_answers=key.get("answers", {}),
        explanations=key.get("explanations", {}),
        transcripts=key.get("transcripts", {}),
        vocabulary=[
            {**v, "already_in_cards": (v["word"].strip().lower(), PartOfSpeech(v["part_of_speech"])) in existing}
            for v in vocabulary
        ],
    )
