"""Lesen exercise generators, one structured-output agent per Teil. The checker that solves each
draft blind before it is saved lives in app.agents.core.checker."""
from pydantic_ai import Agent, NativeOutput

from app.agents.prompts import reading_teil1, reading_teil2, reading_teil3, reading_teil4
from app.schemas.ai_outputs import (
    ReadingTeil1AIOutput,
    ReadingTeil2AIOutput,
    ReadingTeil3AIOutput,
    ReadingTeil4AIOutput,
)

# NativeOutput (JSON-schema constrained decoding) rather than the default tool-call output, so
# these work on local Ollama models without native tool calling as well as on Gemini.
teil1_agent = Agent(
    name="lesen_teil1_generator",
    output_type=NativeOutput(ReadingTeil1AIOutput),
    instructions=reading_teil1.SYSTEM_PROMPT,
)
teil2_agent = Agent(
    name="lesen_teil2_generator",
    output_type=NativeOutput(ReadingTeil2AIOutput),
    instructions=reading_teil2.SYSTEM_PROMPT,
)
teil3_agent = Agent(
    name="lesen_teil3_generator",
    output_type=NativeOutput(ReadingTeil3AIOutput),
    instructions=reading_teil3.SYSTEM_PROMPT,
)
teil4_agent = Agent(
    name="lesen_teil4_generator",
    output_type=NativeOutput(ReadingTeil4AIOutput),
    instructions=reading_teil4.SYSTEM_PROMPT,
)
