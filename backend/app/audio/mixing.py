"""Turn a script (speaker lines) into one WAV file: one voice per speaker, short pauses between
lines, everything resampled to a common rate."""
import io
import wave
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from app.audio.tts import Clip, Gender, TTSEngine


@dataclass(frozen=True)
class Line:
    speaker: str
    gender: Gender
    text: str


@dataclass(frozen=True)
class RenderedAudio:
    wav: bytes
    duration_s: float
    tokens: int


def assign_voices(lines: Sequence[Line], engine: TTSEngine) -> dict[str, str]:
    """Give every distinct speaker their own voice, cycling through the engine's voices per gender,
    so two women in one dialogue don't sound identical (as long as two voices exist)."""
    assigned: dict[str, str] = {}
    used = {"female": 0, "male": 0}
    for line in lines:
        if line.speaker in assigned:
            continue
        pool = engine.voices(line.gender)
        if not pool:
            raise ValueError(f"No {line.gender} voice configured for TTS engine {engine.name}")
        assigned[line.speaker] = pool[used[line.gender] % len(pool)]
        used[line.gender] += 1
    return assigned


def render_script(
    lines: Sequence[Line],
    engine: TTSEngine,
    sample_rate: int = 22050,
    gap_s: float = 0.5,
    lead_s: float = 0.4,
    max_workers: int = 4,
) -> RenderedAudio:
    voices = assign_voices(lines, engine)
    # Lines are independent requests: render them concurrently (matters for the online engine).
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        clips = list(pool.map(lambda line: engine.synthesize(line.text, voices[line.speaker]), lines))

    silence = np.zeros(int(gap_s * sample_rate), dtype=np.float32)
    parts = [np.zeros(int(lead_s * sample_rate), dtype=np.float32)]
    for clip in clips:
        parts.append(resample(clip, sample_rate))
        parts.append(silence)
    samples = np.concatenate(parts)
    return RenderedAudio(
        wav=to_wav(samples, sample_rate),
        duration_s=round(len(samples) / sample_rate, 2),
        tokens=sum(c.tokens for c in clips),
    )


def resample(clip: Clip, target_rate: int) -> np.ndarray:
    if clip.sample_rate == target_rate or len(clip.samples) == 0:
        return clip.samples.astype(np.float32)
    duration = len(clip.samples) / clip.sample_rate
    target_len = int(round(duration * target_rate))
    source_t = np.linspace(0.0, duration, num=len(clip.samples), endpoint=False)
    target_t = np.linspace(0.0, duration, num=target_len, endpoint=False)
    return np.interp(target_t, source_t, clip.samples).astype(np.float32)


def to_wav(samples: np.ndarray, sample_rate: int) -> bytes:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()
