"""Hören: one script generator per Teil, plugged into the shared generate -> check -> revise flow.

The student-visible content never contains the script; the answer key holds the answers,
explanations, transcripts (revealed after submitting) and the vocabulary list. Audio is added
to the content by the service after the checker has agreed with the key.
"""
from functools import partial

from pydantic_ai import Agent, NativeOutput

from app.agents.core.checked import TeilSpec
from app.agents.prompts import hoeren as prompts
from app.schemas.hoeren import (
    PICTURE_CODES,
    HoerenTeil1AIOutput,
    HoerenTeil2AIOutput,
    HoerenTeil3AIOutput,
    HoerenTeil4AIOutput,
    ScriptLine,
)

OPTION_LETTERS = ("A", "B", "C")
JA_NEIN = ("Ja", "Nein")


def _agent(teil: int, output_type, instructions: str) -> Agent:
    return Agent(name=f"hoeren_teil{teil}_generator", output_type=NativeOutput(output_type), instructions=instructions)


teil1_agent = _agent(1, HoerenTeil1AIOutput, prompts.TEIL1)
teil2_agent = _agent(2, HoerenTeil2AIOutput, prompts.TEIL2)
teil3_agent = _agent(3, HoerenTeil3AIOutput, prompts.TEIL3)
teil4_agent = _agent(4, HoerenTeil4AIOutput, prompts.TEIL4)


def _lines(script: list[ScriptLine]) -> list[dict]:
    return [line.model_dump() for line in script]


def _vocab(out) -> list[dict]:
    return [v.model_dump(mode="json") for v in out.vocabulary]


def split_teil1(out: HoerenTeil1AIOutput) -> tuple[dict, dict]:
    items = sorted(out.items, key=lambda i: i.item_number)
    content = {
        "items": [
            {"item_number": i.item_number, "context": i.context, "prompt": i.prompt, "options": i.options}
            for i in items
        ]
    }
    key = {
        "answers": {str(i.item_number): i.correct_option_index for i in items},
        "explanations": {str(i.item_number): i.explanation for i in items},
        "transcripts": {str(i.item_number): _lines(i.script) for i in items},
        "vocabulary": _vocab(out),
    }
    return content, key


def split_teil2(out: HoerenTeil2AIOutput) -> tuple[dict, dict]:
    aufgaben = sorted(out.aufgaben, key=lambda a: a.aufgabe_number)
    content = {
        "context": out.context,
        "beispiel": out.beispiel.model_dump(),  # shown solved, like in the exam
        "pictures": [
            {"code": p.code, "emoji": p.emoji, "caption": p.caption} for p in sorted(out.pictures, key=lambda p: p.code)
        ],
        "aufgaben": [{"aufgabe_number": a.aufgabe_number, "label": a.label} for a in aufgaben],
    }
    key = {
        "answers": {str(a.aufgabe_number): a.correct_code for a in aufgaben},
        "explanations": {str(a.aufgabe_number): a.explanation for a in aufgaben},
        "transcripts": {"all": _lines(out.script)},
        "vocabulary": _vocab(out),
    }
    return content, key


def split_teil3(out: HoerenTeil3AIOutput) -> tuple[dict, dict]:
    items = sorted(out.items, key=lambda i: i.item_number)
    content = {
        "items": [
            {
                "item_number": i.item_number,
                "context": i.context,
                "prompt": i.prompt,
                "options": [{"emoji": o.emoji, "caption": o.caption} for o in i.options],
            }
            for i in items
        ]
    }
    key = {
        "answers": {str(i.item_number): i.correct_option_index for i in items},
        "explanations": {str(i.item_number): i.explanation for i in items},
        "transcripts": {str(i.item_number): _lines(i.script) for i in items},
        "vocabulary": _vocab(out),
    }
    return content, key


def split_teil4(out: HoerenTeil4AIOutput) -> tuple[dict, dict]:
    statements = sorted(out.statements, key=lambda s: s.number)
    content = {
        "context": out.context,
        "statements": [{"number": s.number, "statement": s.statement} for s in statements],
    }
    key = {
        "answers": {str(s.number): s.answer for s in statements},
        "explanations": {str(s.number): s.explanation for s in statements},
        "transcripts": {"all": _lines(out.script)},
        "vocabulary": _vocab(out),
    }
    return content, key


def scripts(out) -> dict[str, list[ScriptLine]]:
    """Audio segments to synthesize, keyed like the transcripts ('1'..'5', '11'..'15' or 'all')."""
    if isinstance(out, (HoerenTeil1AIOutput, HoerenTeil3AIOutput)):
        return {str(i.item_number): i.script for i in out.items}
    return {"all": out.script}


def _with_transcripts(split, out, content: dict) -> dict:
    """What the checker sees: the student's view plus what is said (it can't hear audio)."""
    _, key = split(out)
    return {**content, "transcripts": key["transcripts"]}


def _letter(index: int | str) -> str:
    return OPTION_LETTERS[int(index)]


_LETTER_FORMAT = 'the letter of the correct option: "A" for the first, "B" for the second, "C" for the third'


def _spec(teil, agent, split, title, answer_format, allowed, key_to_answer) -> TeilSpec:
    return TeilSpec(
        teil=teil,
        generator=agent,
        build_prompt=partial(prompts.build_user_prompt, teil),
        split=split,
        title=title,
        answer_format=answer_format,
        allowed_answers=allowed,
        key_to_answer=key_to_answer,
        skill="hoeren",
        checker_view=partial(_with_transcripts, split),
    )


SPECS: dict[int, TeilSpec] = {
    1: _spec(1, teil1_agent, split_teil1, lambda out, topic: f"Kurze Texte: {topic}" if topic else "Kurze Texte",
             f"For each item_number (1-5), {_LETTER_FORMAT}.", OPTION_LETTERS, _letter),
    2: _spec(2, teil2_agent, split_teil2, lambda out, topic: f"Gespräch: {topic}" if topic else "Gespräch",
             "For each aufgabe_number (6-10), the code of the matching picture (a-i). Each picture fits at most "
             "one Aufgabe, and the Beispiel's picture is already used.",
             tuple(PICTURE_CODES), str),
    3: _spec(3, teil3_agent, split_teil3, lambda out, topic: f"Kurze Gespräche: {topic}" if topic else "Kurze Gespräche",
             f"For each item_number (11-15), {_LETTER_FORMAT}.", OPTION_LETTERS, _letter),
    4: _spec(4, teil4_agent, split_teil4, lambda out, topic: f"Interview: {topic}" if topic else "Interview",
             'For each statement number (16-20), "Ja" if the interview says so, otherwise "Nein".',
             JA_NEIN, lambda answer: str(answer).capitalize()),
}

# How often the exam plays each Teil's audio.
PLAYS = {1: 2, 2: 1, 3: 1, 4: 2}
