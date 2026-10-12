"""Text-to-speech engines. Each line of a script is synthesized on its own in its speaker's voice
and the mixer joins them, so both engines go through the same, simple single-voice interface.

- Piper: offline, free, ~20-30x faster than real time on CPU. Voice models ship in the image.
- Gemini TTS: online, more natural; token usage is reported so it can be recorded in ai_runs.
"""
import io
import threading
import wave
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol

import numpy as np

from app.config import Settings, get_settings

Gender = Literal["female", "male"]


@dataclass
class Clip:
    samples: np.ndarray  # float32 mono, -1..1
    sample_rate: int
    tokens: int = 0


class TTSEngine(Protocol):
    name: str

    def voices(self, gender: Gender) -> list[str]: ...

    def synthesize(self, text: str, voice: str) -> Clip: ...


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class PiperEngine:
    voices_dir: Path
    female: list[str]
    male: list[str]
    length_scale: float
    name: str = "piper"
    _loaded: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def voices(self, gender: Gender) -> list[str]:
        return self.female if gender == "female" else self.male

    def synthesize(self, text: str, voice: str) -> Clip:
        from piper import SynthesisConfig  # imported lazily: onnxruntime is heavy

        model = self._voice(voice)
        chunks = list(model.synthesize(text, SynthesisConfig(length_scale=self.length_scale)))
        if not chunks:
            return Clip(np.zeros(0, dtype=np.float32), model.config.sample_rate)
        samples = np.concatenate([c.audio_float_array.astype(np.float32) for c in chunks])
        return Clip(samples, chunks[0].sample_rate)

    def _voice(self, voice: str):
        from piper import PiperVoice

        with self._lock:
            if voice not in self._loaded:
                path = self.voices_dir / f"{voice}.onnx"
                if not path.exists():
                    raise FileNotFoundError(f"Piper voice model not found: {path}")
                self._loaded[voice] = PiperVoice.load(path)
            return self._loaded[voice]


@dataclass
class GeminiTTSEngine:
    api_key: str
    model: str
    female: list[str]
    male: list[str]
    name: str = "gemini"

    def voices(self, gender: Gender) -> list[str]:
        return self.female if gender == "female" else self.male

    def synthesize(self, text: str, voice: str) -> Clip:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))
            ),
        )
        response = client.models.generate_content(model=self.model, contents=text, config=config)
        data = response.candidates[0].content.parts[0].inline_data.data
        samples, rate = _decode_pcm_or_wav(data, default_rate=24000)
        usage = response.usage_metadata
        tokens = (usage.prompt_token_count or 0) + (usage.candidates_token_count or 0) if usage else 0
        return Clip(samples, rate, tokens=tokens)


def _decode_pcm_or_wav(data: bytes, default_rate: int) -> tuple[np.ndarray, int]:
    """Gemini returns 16-bit mono PCM, sometimes already wrapped in a WAV container."""
    if data[:4] == b"RIFF":
        with wave.open(io.BytesIO(data)) as w:
            rate = w.getframerate()
            data = w.readframes(w.getnframes())
    else:
        rate = default_rate
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0, rate


def build_engine(settings: Settings) -> TTSEngine:
    if settings.tts_provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("TTS_PROVIDER=gemini needs GEMINI_API_KEY")
        return GeminiTTSEngine(
            api_key=settings.gemini_api_key,
            model=settings.gemini_tts_model,
            female=_split_csv(settings.gemini_tts_female_voices),
            male=_split_csv(settings.gemini_tts_male_voices),
        )
    return PiperEngine(
        voices_dir=Path(settings.piper_voices_dir),
        female=_split_csv(settings.piper_female_voices),
        male=_split_csv(settings.piper_male_voices),
        length_scale=settings.piper_length_scale,
    )


@lru_cache
def get_tts_engine() -> TTSEngine:
    return build_engine(get_settings())
