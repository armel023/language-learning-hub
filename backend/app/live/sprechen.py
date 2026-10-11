"""Live Sprechen sessions: browser <-> this WebSocket <-> Gemini Live (via Pydantic AI realtime).

Protocol on the browser WebSocket:
- browser -> server: binary frames of 16-bit mono PCM at `input_rate` (microphone), and
  JSON {"type": "stop"} to end the conversation.
- server -> browser: JSON {"type": "ready", input_rate, output_rate, max_seconds} once connected,
  binary frames of 16-bit mono PCM at `output_rate` (the partner's voice),
  JSON {"type": "transcript", index, speaker, text} (live captions, keyed by turn),
  JSON {"type": "interrupted"} (the candidate started talking: stop playback),
  JSON {"type": "ended", attempt_id} once the transcript is saved and grading has started,
  JSON {"type": "error", message}.

The API key stays on the server; the browser only ever talks to this app.
"""
import asyncio
import contextlib
import json
import logging
import time
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from opentelemetry import trace
from pydantic_ai import Agent
from pydantic_ai.messages import RealtimeInputSpeechStartEvent, RealtimeResponseInterruptedEvent
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.realtime.google import GoogleRealtimeModel
from pydantic_ai.usage import RunUsage
from starlette.concurrency import run_in_threadpool

from app.agents import sprechen
from app.config import get_settings
from app.db.session import SessionLocal
from app.models import AIRun, AIRunStatus, Exercise
from app.repositories import ai_run_repo
from app.services import sprechen_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Sent as text, not speech, so it starts the partner without appearing in the transcript.
_START_CUE = "Die Prüfung beginnt jetzt. Beginne bitte das Gespräch."


def _realtime_model(teil: int, partner_gender: str | None) -> GoogleRealtimeModel:
    settings = get_settings()
    voice = settings.gemini_live_male_voice if partner_gender == "male" else settings.gemini_live_female_voice
    model_settings = {"google_voice": voice, "google_transcription_language_codes": ["de-DE"]}
    if teil == 2:
        # Monologue: let the model stay silent instead of answering every pause. Proactive audio is
        # only available on the Gemini Developer API's v1alpha.
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key, http_options={"api_version": "v1alpha"})
        return GoogleRealtimeModel(
            settings.gemini_live_model, provider=GoogleProvider(client=client),
            settings={**model_settings, "google_proactive_audio": True},
        )
    return GoogleRealtimeModel(
        settings.gemini_live_model, provider=GoogleProvider(api_key=settings.gemini_api_key), settings=model_settings
    )


async def run_session(websocket: WebSocket, exercise_id: uuid.UUID, user_id: uuid.UUID) -> None:
    settings = get_settings()
    exercise: Exercise | None = await run_in_threadpool(_load_exercise, exercise_id)
    if exercise is None:
        await _send_error(websocket, "Sprechen exercise not found.")
        return
    if not settings.gemini_api_key:
        await _send_error(websocket, "Live conversation needs GEMINI_API_KEY (it runs on Gemini Live).")
        return
    if await run_in_threadpool(_budget_used_up, user_id):
        await _send_error(websocket, "Daily AI token budget used up. It resets at 00:00 UTC.")
        return

    teil, content, hidden = exercise.teil, exercise.content, exercise.answer_key or {}
    agent = Agent(name="sprechen_partner", instructions=sprechen.partner_instructions(teil, content, hidden))
    usage = RunUsage()
    turns: dict[int, dict] = {}
    started = time.monotonic()
    error: str | None = None

    with tracer.start_as_current_span("sprechen_live") as span:
        span.set_attribute("app.exercise_id", str(exercise_id))
        try:
            model = _realtime_model(teil, hidden.get("partner_gender"))
            async with agent.realtime(model, usage=usage).session() as session:
                await websocket.send_json({
                    "type": "ready",
                    "input_rate": session.audio_input_sample_rate,
                    "output_rate": session.audio_output_sample_rate,
                    "max_seconds": settings.sprechen_max_session_seconds,
                })
                if sprechen.partner_starts(teil):
                    await session.send(_START_CUE)
                await _bridge(websocket, session, turns, settings.sprechen_max_session_seconds)
        except WebSocketDisconnect:
            pass
        except Exception as exc:  # noqa: BLE001 - surface to the user, keep whatever transcript exists
            logger.exception("Live Sprechen session failed")
            error = f"The live connection failed: {exc}"

    duration = time.monotonic() - started
    transcript = merge_turns([turns[i] for i in sorted(turns)])
    attempt_id = await run_in_threadpool(_finish, exercise_id, user_id, transcript, usage, duration, error)
    with contextlib.suppress(Exception):
        if error and attempt_id is None:
            await _send_error(websocket, error)
        else:
            await websocket.send_json({"type": "ended", "attempt_id": str(attempt_id) if attempt_id else None,
                                       "error": error})
        await websocket.close()


async def _bridge(websocket: WebSocket, session, turns: dict[int, dict], max_seconds: int) -> None:
    async def partner_audio():
        async for chunk in session.stream_audio():
            await websocket.send_bytes(chunk)

    async def captions():
        async for update in session.stream_transcripts(delta=True):
            role = "candidate" if update.speaker == "user" else "partner"
            turns[update.index] = {"role": role, "text": update.transcript}
            await websocket.send_json({"type": "transcript", "index": update.index, "speaker": role,
                                       "text": update.transcript})

    async def barge_in():
        async for event in session:
            if isinstance(event, (RealtimeInputSpeechStartEvent, RealtimeResponseInterruptedEvent)):
                await websocket.send_json({"type": "interrupted"})

    async def microphone():
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            if message.get("bytes"):
                await session.send_audio(message["bytes"])
            elif message.get("text") and json.loads(message["text"]).get("type") == "stop":
                return

    background = [asyncio.create_task(c()) for c in (partner_audio, captions, barge_in)]
    ending = [asyncio.create_task(microphone()), asyncio.create_task(asyncio.sleep(max_seconds))]
    try:
        done, _ = await asyncio.wait(ending + background, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task in background and task.exception():
                raise task.exception()
    finally:
        for task in ending + background:
            task.cancel()
        await asyncio.gather(*ending, *background, return_exceptions=True)


def merge_turns(turns: list[dict]) -> list[dict]:
    """Drop empty turns and join consecutive turns by the same speaker: a pause mid-sentence makes
    speech recognition start a new turn, which would otherwise split one answer in two."""
    merged: list[dict] = []
    for turn in turns:
        text = turn["text"].strip()
        if not text:
            continue
        if merged and merged[-1]["role"] == turn["role"]:
            merged[-1] = {"role": turn["role"], "text": f"{merged[-1]['text']} {text}"}
        else:
            merged.append({"role": turn["role"], "text": text})
    return merged


# --- sync helpers (run in the threadpool) --------------------------------------------------------


def _load_exercise(exercise_id: uuid.UUID) -> Exercise | None:
    db = SessionLocal()
    try:
        exercise = db.get(Exercise, exercise_id)
        if exercise is None or exercise.skill.value != "sprechen":
            return None
        db.expunge(exercise)
        return exercise
    finally:
        db.close()


def _budget_used_up(user_id: uuid.UUID) -> bool:
    budget = get_settings().ai_daily_token_budget
    if budget <= 0:
        return False
    db = SessionLocal()
    try:
        return ai_run_repo.tokens_used_today(db, user_id) >= budget
    finally:
        db.close()


def _finish(exercise_id, user_id, transcript, usage: RunUsage, duration: float, error: str | None):
    settings = get_settings()
    db = SessionLocal()
    try:
        ai_run_repo.create_run(db, AIRun(
            user_id=user_id, feature="sprechen_live", provider="gemini", model_name=settings.gemini_live_model,
            status=AIRunStatus.FAILED if error else AIRunStatus.SUCCEEDED,
            requests=usage.requests, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens, latency_ms=int(duration * 1000), error_message=error,
        ))
        if not any(t["role"] == "candidate" for t in transcript):
            return None
        attempt = sprechen_service.save_session(db, user_id, exercise_id, transcript, duration)
        return attempt.id
    finally:
        db.close()


async def _send_error(websocket: WebSocket, message: str) -> None:
    with contextlib.suppress(Exception):
        await websocket.send_json({"type": "error", "message": message})
        await websocket.close()
