"""AI output schemas for Hören. Each exercise is a script (what is said, by whom) plus the
questions; audio is synthesized from the script only after the checker has verified it.

The validators encode the exam rules that the model must not get wrong; a violation goes back to
the model with the reason (Pydantic AI retries on validation errors).

Script and vocabulary lengths are checked in validators rather than as min/max items on the
fields: Gemini rejects a response schema whose list-length ranges make it too complex
(400 INVALID_ARGUMENT). Only small exact counts (5 questions, 3 options, 9 pictures) stay
in the schema.
"""
import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.ai_outputs import ExtractedVocabEntry

PICTURE_CODES = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]


class ScriptLine(BaseModel):
    speaker: str = Field(description="A first name or role, e.g. 'Anna', 'Moderator', 'Ansage'.")
    gender: Literal["female", "male"] = Field(description="Decides the voice.")
    text: str = Field(description="What this speaker says, in simple A2 German.")


class Picture(BaseModel):
    """Shown as an icon card: a single emoji plus a short German caption."""

    emoji: str = Field(description="Exactly one emoji that depicts the caption.")
    caption: str = Field(description="1-3 German words, e.g. 'schwimmen', 'ein Fahrrad'.")
    keyword: str = Field(description="One word from the caption that literally appears in the script.")

    @field_validator("emoji")
    @classmethod
    def short_emoji(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 8 or any(ch.isalnum() for ch in v):
            raise ValueError("emoji must be a single emoji character, no letters")
        return v


def _script_text(lines: list[ScriptLine]) -> str:
    return " ".join(line.text for line in lines).lower()


def _mentions(lines: list[ScriptLine], word: str) -> bool:
    return word.strip().lower() in _script_text(lines)


def _length(items: list, low: int, high: int, what: str) -> None:
    if not low <= len(items) <= high:
        raise ValueError(f"{what} must have {low}-{high} entries, got {len(items)}")


def _numbered(numbers: list[int], expected: list[int], what: str) -> None:
    if sorted(numbers) != expected:
        raise ValueError(f"{what} must be numbered {expected} with no duplicates, got {sorted(numbers)}")


# --- Teil 1: five short texts, one 3-option question each, each played twice ----------------


class HoerenTeil1Item(BaseModel):
    item_number: int = Field(ge=1, le=5)
    context: str = Field(description="Shown before listening, e.g. 'Sie hören eine Nachricht auf dem Anrufbeantworter.'")
    script: list[ScriptLine] = Field(description="1-6 lines: announcement, phone message, radio, or short exchange.")
    prompt: str = Field(description="The question in German.")
    options: list[str] = Field(min_length=3, max_length=3)
    correct_option_index: int = Field(ge=0, le=2)
    explanation: str = Field(description="One short A2 German sentence quoting what decides it.")


class HoerenTeil1AIOutput(BaseModel):
    items: list[HoerenTeil1Item] = Field(min_length=5, max_length=5)
    vocabulary: list[ExtractedVocabEntry] = Field(description="4-10 useful A2 words heard in the texts.")

    @model_validator(mode="after")
    def check(self) -> "HoerenTeil1AIOutput":
        _numbered([i.item_number for i in self.items], [1, 2, 3, 4, 5], "items")
        for item in self.items:
            _length(item.script, 1, 6, f"item {item.item_number} script")
        _length(self.vocabulary, 4, 10, "vocabulary")
        return self


# --- Teil 2: one dialogue, match 5 time labels to 5 of 9 pictures, played once ----------------


class HoerenTeil2Beispiel(BaseModel):
    label: str = Field(description="The example's time label, e.g. 'Montag'.")
    correct_code: str
    explanation: str


class HoerenTeil2Aufgabe(BaseModel):
    aufgabe_number: int = Field(ge=6, le=10)
    label: str = Field(description="A time label of the same kind, e.g. 'Dienstag', 'März', '15 Uhr'.")
    correct_code: str
    explanation: str


class HoerenTeil2Picture(Picture):
    code: str


class HoerenTeil2AIOutput(BaseModel):
    context: str = Field(description="Shown before listening, e.g. 'Was macht Lena nächste Woche?'")
    script: list[ScriptLine] = Field(description="8-30 lines of dialogue.")
    beispiel: HoerenTeil2Beispiel
    aufgaben: list[HoerenTeil2Aufgabe] = Field(min_length=5, max_length=5)
    pictures: list[HoerenTeil2Picture] = Field(min_length=9, max_length=9, description="Activities a-i.")
    vocabulary: list[ExtractedVocabEntry] = Field(description="4-10 useful A2 words heard in the audio.")

    @model_validator(mode="after")
    def check(self) -> "HoerenTeil2AIOutput":
        _numbered([a.aufgabe_number for a in self.aufgaben], [6, 7, 8, 9, 10], "aufgaben")
        _length(self.script, 8, 30, "script")
        _length(self.vocabulary, 4, 10, "vocabulary")
        codes = [p.code for p in self.pictures]
        if sorted(codes) != PICTURE_CODES:
            raise ValueError(f"pictures must use the codes {PICTURE_CODES}, one each")
        answers = [self.beispiel.correct_code, *(a.correct_code for a in self.aufgaben)]
        if any(code not in PICTURE_CODES for code in answers):
            raise ValueError("every correct_code must be one of the picture codes a-i")
        if len(set(answers)) != len(answers):
            raise ValueError("each picture may be the answer only once (including the Beispiel)")
        labels = [self.beispiel.label, *(a.label for a in self.aufgaben)]
        if len({label.lower() for label in labels}) != len(labels):
            raise ValueError("the six time labels (Beispiel + 6-10) must all be different")
        missing = [label for label in labels if not _mentions(self.script, label)]
        if missing:
            raise ValueError(f"these labels are never said in the dialogue: {missing}")
        by_code = {p.code: p for p in self.pictures}
        unheard = [c for c in answers if not _mentions(self.script, by_code[c].keyword)]
        if unheard:
            raise ValueError(
                f"the keyword of each correct picture must be said in the dialogue; not found for {unheard}"
            )
        return self


# --- Teil 3: five short dialogues, pick 1 of 3 pictures, played once -------------------------


class HoerenTeil3Item(BaseModel):
    item_number: int = Field(ge=11, le=15)
    context: str = Field(description="Shown before listening, e.g. 'Was kauft die Frau?'")
    script: list[ScriptLine] = Field(description="2-8 lines of dialogue.")
    prompt: str
    options: list[Picture] = Field(min_length=3, max_length=3)
    correct_option_index: int = Field(ge=0, le=2)
    explanation: str


class HoerenTeil3AIOutput(BaseModel):
    items: list[HoerenTeil3Item] = Field(min_length=5, max_length=5)
    vocabulary: list[ExtractedVocabEntry] = Field(description="4-10 useful A2 words heard in the audio.")

    @model_validator(mode="after")
    def check(self) -> "HoerenTeil3AIOutput":
        _numbered([i.item_number for i in self.items], [11, 12, 13, 14, 15], "items")
        _length(self.vocabulary, 4, 10, "vocabulary")
        for item in self.items:
            _length(item.script, 2, 8, f"item {item.item_number} script")
            # The exam's trick: all three pictures are mentioned, only one is the answer.
            unheard = [o.keyword for o in item.options if not _mentions(item.script, o.keyword)]
            if unheard:
                raise ValueError(
                    f"item {item.item_number}: every option must be mentioned in its dialogue; "
                    f"these keywords are never said: {unheard}"
                )
        return self


# --- Teil 4: one interview, five ja/nein statements, played twice -----------------------------


class HoerenTeil4Statement(BaseModel):
    number: int = Field(ge=16, le=20)
    statement: str
    answer: Literal["ja", "nein"]
    explanation: str


class HoerenTeil4AIOutput(BaseModel):
    context: str = Field(description="Shown before listening, e.g. 'Sie hören ein Interview mit einer Köchin.'")
    script: list[ScriptLine] = Field(description="10-40 lines of interview.")
    statements: list[HoerenTeil4Statement] = Field(min_length=5, max_length=5)
    vocabulary: list[ExtractedVocabEntry] = Field(description="4-10 useful A2 words heard in the audio.")

    @model_validator(mode="after")
    def check(self) -> "HoerenTeil4AIOutput":
        _numbered([s.number for s in self.statements], [16, 17, 18, 19, 20], "statements")
        _length(self.script, 10, 40, "script")
        _length(self.vocabulary, 4, 10, "vocabulary")
        answers = {s.answer for s in self.statements}
        if answers != {"ja", "nein"}:
            raise ValueError("include both 'ja' and 'nein' statements")
        if len({line.speaker for line in self.script}) < 2:
            raise ValueError("the interview needs two speakers")
        return self


# --- API ---------------------------------------------------------------------------------


class HoerenGenerateRequest(BaseModel):
    teil: Literal[1, 2, 3, 4]
    topic: str | None = None
    level: str = "A2"


class HoerenAttemptResult(BaseModel):
    """Like the Lesen result, plus what was said (revealed only after submitting) and the
    exercise's vocabulary, flagged where the user already has a card."""

    id: uuid.UUID
    exercise_id: uuid.UUID
    score: int
    max_score: int
    is_correct_per_question: dict[str, bool]
    correct_answers: dict[str, int | str]
    explanations: dict[str, str]
    transcripts: dict[str, list[dict]]
    vocabulary: list[dict]
