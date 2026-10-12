"""Sprechen cards and grading.

Generated cards are split in two: what the candidate sees (their card) and what only the live
partner sees (the partner's card, persona, calendar). Validators enforce what must hold for the
task to be doable, e.g. that two calendars share a free slot.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import AttemptStatus

# --- Teil 1: Fragen zur Person ---------------------------------------------------------------


class PersonaFact(BaseModel):
    card: str = Field(description="One of the candidate's card keywords, exactly as written.")
    answer: str = Field(description="What the partner says about this, 2-3 short A2 German sentences.")


class SprechenTeil1AI(BaseModel):
    candidate_cards: list[str] = Field(min_length=4, max_length=4, description="Keywords like 'Geburtstag?'.")
    partner_cards: list[str] = Field(min_length=4, max_length=4)
    partner_name: str
    partner_gender: Literal["female", "male"]
    partner_facts: list[PersonaFact] = Field(min_length=4, max_length=4, description="One per candidate card.")

    @model_validator(mode="after")
    def check(self) -> "SprechenTeil1AI":
        cards = [c.strip() for c in self.candidate_cards + self.partner_cards]
        if len({c.lower() for c in cards}) != 8:
            raise ValueError("all 8 cards must be different")
        if not all(c.endswith("?") and len(c) <= 30 for c in cards):
            raise ValueError("each card is one short keyword ending in '?', e.g. 'Wohnort?'")
        if sorted(f.card.strip() for f in self.partner_facts) != sorted(c.strip() for c in self.candidate_cards):
            raise ValueError("partner_facts must have exactly one entry per candidate card, using the same keyword")
        return self


# --- Teil 2: von sich erzählen -----------------------------------------------------------------


class SprechenTeil2AI(BaseModel):
    question: str = Field(description="The central question, e.g. 'Was machen Sie oft am Wochenende?'")
    prompts: list[str] = Field(min_length=4, max_length=4, description="Four corner prompts, e.g. 'Mit wem?', 'Sport, ...?'")

    @model_validator(mode="after")
    def check(self) -> "SprechenTeil2AI":
        if not self.question.strip().endswith("?"):
            raise ValueError("the central question must end with '?'")
        if len({p.strip().lower() for p in self.prompts}) != 4 or not all(p.strip().endswith("?") for p in self.prompts):
            raise ValueError("the four prompts must be different and each end with '?'")
        return self


# --- Teil 3: gemeinsam etwas planen --------------------------------------------------------------

FIRST_HOUR, LAST_HOUR = 7, 22  # calendar rows 7.00 .. 21.00; an entry ends at most at 22


class CalendarEntry(BaseModel):
    start: int = Field(description="Start hour, 7-21.")
    end: int = Field(description="End hour (exclusive), start+1 .. 22.")
    text: str = Field(description="Short German note, e.g. 'Fahrrad abholen'.")


def busy_hours(entries: list[CalendarEntry]) -> set[int]:
    return {h for e in entries for h in range(e.start, e.end)}


def common_free_hours(a: list[CalendarEntry], b: list[CalendarEntry]) -> list[int]:
    busy = busy_hours(a) | busy_hours(b)
    return [h for h in range(FIRST_HOUR, LAST_HOUR) if h not in busy]


class SprechenTeil3TerminAI(BaseModel):
    situation: str = Field(description="e.g. 'Ihr Freund Patrick hat Geburtstag. Sie möchten ein Geschenk für ihn kaufen. Finden Sie einen Termin.'")
    day: str = Field(description="e.g. 'Samstag, 17. Mai'")
    candidate_calendar: list[CalendarEntry]
    partner_calendar: list[CalendarEntry]
    partner_name: str
    partner_gender: Literal["female", "male"]

    @model_validator(mode="after")
    def check(self) -> "SprechenTeil3TerminAI":
        for who, cal in (("candidate", self.candidate_calendar), ("partner", self.partner_calendar)):
            if not 4 <= len(cal) <= 8:
                raise ValueError(f"{who}_calendar needs 4-8 entries")
            for e in cal:
                if not (FIRST_HOUR <= e.start < e.end <= LAST_HOUR):
                    raise ValueError(f"{who} entry '{e.text}' must lie between 7 and 22 with start < end")
            hours = [h for e in cal for h in range(e.start, e.end)]
            if len(hours) != len(set(hours)):
                raise ValueError(f"{who}_calendar entries must not overlap")
        free = common_free_hours(self.candidate_calendar, self.partner_calendar)
        if not free:
            raise ValueError("the two calendars must share at least one free hour (the meeting slot)")
        if len(free) > 3:
            raise ValueError(f"too easy: the calendars share {len(free)} free hours; make it 1-3 so they must negotiate")
        return self


class SprechenTeil3PlanenAI(BaseModel):
    situation: str = Field(description="e.g. 'Ihr Deutschkurs ist zu Ende. Sie planen eine Party. Was wollen Sie organisieren?'")
    center: str = Field(description="The mind map's centre, e.g. 'Party'.")
    candidate_points: list[str] = Field(min_length=5, max_length=5, description="Five aspects on the candidate's card.")
    partner_points: list[str] = Field(min_length=5, max_length=5, description="Five different aspects on the partner's card.")
    partner_name: str
    partner_gender: Literal["female", "male"]

    @model_validator(mode="after")
    def check(self) -> "SprechenTeil3PlanenAI":
        mine = {p.strip().lower() for p in self.candidate_points}
        theirs = {p.strip().lower() for p in self.partner_points}
        if len(mine) != 5 or len(theirs) != 5:
            raise ValueError("each card needs five different points")
        if mine & theirs:
            raise ValueError(f"the two cards must have different points; shared: {sorted(mine & theirs)}")
        return self


# --- grading -------------------------------------------------------------------------------------


class ChecklistItem(BaseModel):
    item: str = Field(description="A card keyword, prompt or task step, exactly as given.")
    done: bool
    comment: str = Field(description="One short English sentence: what the candidate said, or what was missing.")


class CriterionGrade(BaseModel):
    score: int = Field(ge=0, le=3)
    comment: str


class Correction(BaseModel):
    original: str = Field(description="The candidate's words, as transcribed.")
    corrected: str
    explanation: str = Field(description="Short, simple English explanation.")


class SprechenGradeAI(BaseModel):
    checklist: list[ChecklistItem]
    interaction: CriterionGrade = Field(description="Teil 1/3: asks, answers, reacts, keeps the exchange going. Teil 2: coherent, connected speech.")
    accuracy: CriterionGrade = Field(description="Grammar and vocabulary, judged by whether errors hinder understanding.")
    corrections: list[Correction] = Field(description="The most useful corrections, at most 6.")
    better_phrases: list[str] = Field(description="2-4 natural A2 sentences the candidate could have used here.")
    summary: str = Field(description="2-3 encouraging, concrete sentences in English.")


# --- API -----------------------------------------------------------------------------------------


class SprechenGenerateRequest(BaseModel):
    teil: Literal[1, 2, 3]
    topic: str | None = None
    level: str = "A2"
    # Teil 3 only: "termin" (find a time) or "planen" (plan something together); None = either.
    variant: Literal["termin", "planen"] | None = None


class SprechenAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_id: uuid.UUID
    status: AttemptStatus
    score: int | None
    max_score: int
    transcript: list | None
    rubric_scores: dict | None
    feedback: dict | None
    submitted_at: datetime | None
