"""Sprechen: card generators, the live partner's instructions, and the transcript grader.

Cards are split into what the candidate sees and what only the partner knows; the partner is a
Gemini Live voice agent whose instructions are built from its hidden card. After the session a
text agent grades the transcript; task coverage is scored in code from its checklist.
"""
import random
from dataclasses import dataclass

from pydantic_ai import Agent, ModelRetry, NativeOutput, RunContext

from app.schemas.sprechen import (
    LAST_HOUR,
    CalendarEntry,
    SprechenGradeAI,
    SprechenTeil1AI,
    SprechenTeil2AI,
    SprechenTeil3PlanenAI,
    SprechenTeil3TerminAI,
)

_LANGUAGE = """Everything on the cards and in the facts is simple A2 German. Cards contain keywords,
not full sentences, like the Goethe-Zertifikat A2 cards."""

teil1_agent = Agent(
    name="sprechen_teil1_generator",
    output_type=NativeOutput(SprechenTeil1AI),
    instructions=f"""You write Goethe-Zertifikat A2 Sprechen Teil 1 cards ("Fragen zur Person").
The candidate gets four cards and asks the partner four questions with them; then the partner asks
four questions with its own four cards. Each card is one personal topic as a keyword with a
question mark, e.g. 'Geburtstag?', 'Wohnort?', 'Beruf?', 'Hobby?', 'Eltern?', 'Musik?',
'Familienname?', 'Ausbildung/Studium?'. All eight are different. Also invent the partner: a first
name, gender, and for each of the candidate's four cards what the partner would answer
(2-3 short sentences, consistent with each other). {_LANGUAGE}""",
)

teil2_agent = Agent(
    name="sprechen_teil2_generator",
    output_type=NativeOutput(SprechenTeil2AI),
    instructions=f"""You write Goethe-Zertifikat A2 Sprechen Teil 2 cards ("von sich erzählen").
The candidate talks about their own life. The card has one central question in the 'Sie' form,
e.g. 'Was machen Sie oft am Wochenende?' or 'Was machen Sie mit Ihrem Geld?', and four short
prompts around it that the candidate must address, e.g. 'Mit wem?', 'Wo?', 'Sport, ...?',
'Sparen?'. At most one prompt may be open-ended with '...?'. {_LANGUAGE}""",
)

teil3_termin_agent = Agent(
    name="sprechen_teil3_termin_generator",
    output_type=NativeOutput(SprechenTeil3TerminAI),
    instructions=f"""You write Goethe-Zertifikat A2 Sprechen Teil 3 tasks of the type "einen Termin finden".
Two people want to do something together on one day and must find a time. Each gets a
different calendar for that day (hours 7-22) with 4-8 entries such as 'lange schlafen' (7-10),
'Frühstück bei Mario' (11-13), 'Fahrrad abholen' (14-15), 'Fußball-Training' (18-19). Entries
may span several hours and must not overlap within one calendar. The two calendars together
must leave only 1-3 common free hours, so the candidates have to propose, reject and negotiate.
Also give the partner a first name and gender. {_LANGUAGE}""",
)

teil3_planen_agent = Agent(
    name="sprechen_teil3_planen_generator",
    output_type=NativeOutput(SprechenTeil3PlanenAI),
    instructions=f"""You write Goethe-Zertifikat A2 Sprechen Teil 3 tasks of the type "gemeinsam etwas planen".
Two people plan something together, e.g. a party at the end of the German course, a trip, a
present for a friend. Each gets a mind map with the same centre word and five DIFFERENT aspects
to discuss (candidate e.g. 'Termin', 'Essen', 'tanzen', 'Quiz', 'Theater'; partner e.g. 'Ort',
'Getränke', 'Musik', 'Fotos', 'Einladung'). Also give the partner a first name and gender. {_LANGUAGE}""",
)


def build_generator_prompt(teil: int, topic: str | None, level: str) -> str:
    topic_line = f"Topic: {topic}" if topic else "Topic: pick an everyday A2 topic."
    return f"Write {level} Sprechen Teil {teil} material.\n{topic_line}"


# --- candidate view vs. partner's hidden card ----------------------------------------------------


def split_teil1(out: SprechenTeil1AI) -> tuple[dict, dict]:
    return (
        {"heading": "Fragen zur Person", "cards": out.candidate_cards},
        {
            "partner_name": out.partner_name,
            "partner_gender": out.partner_gender,
            "partner_cards": out.partner_cards,
            "partner_facts": {f.card: f.answer for f in out.partner_facts},
        },
    )


def split_teil2(out: SprechenTeil2AI) -> tuple[dict, dict]:
    return {"heading": "von sich erzählen", "question": out.question, "prompts": out.prompts}, {}


def _calendar(entries: list[CalendarEntry]) -> list[dict]:
    return [e.model_dump() for e in sorted(entries, key=lambda e: e.start)]


def split_teil3_termin(out: SprechenTeil3TerminAI) -> tuple[dict, dict]:
    return (
        {"variant": "termin", "situation": out.situation, "day": out.day, "calendar": _calendar(out.candidate_calendar)},
        {
            "partner_name": out.partner_name,
            "partner_gender": out.partner_gender,
            "partner_calendar": _calendar(out.partner_calendar),
        },
    )


def split_teil3_planen(out: SprechenTeil3PlanenAI) -> tuple[dict, dict]:
    return (
        {"variant": "planen", "situation": out.situation, "center": out.center, "points": out.candidate_points},
        {"partner_name": out.partner_name, "partner_gender": out.partner_gender, "partner_points": out.partner_points},
    )


@dataclass(frozen=True)
class CardSpec:
    agent: Agent
    split: object
    title: object


def card_spec(teil: int, variant: str | None) -> CardSpec:
    if teil == 1:
        return CardSpec(teil1_agent, split_teil1, lambda out: "Fragen zur Person")
    if teil == 2:
        return CardSpec(teil2_agent, split_teil2, lambda out: out.question)
    variant = variant or random.choice(["termin", "planen"])
    if variant == "termin":
        return CardSpec(teil3_termin_agent, split_teil3_termin, lambda out: f"Termin finden: {out.day}")
    return CardSpec(teil3_planen_agent, split_teil3_planen, lambda out: f"Planen: {out.center}")


# --- the live partner ----------------------------------------------------------------------------

_PARTNER_RULES = """You are a candidate's conversation partner in an oral Goethe-Zertifikat A2 exam
(Sprechen). Speak only German, simply and clearly, at A2 level, a little slower than normal.
Behave like a real exam partner: keep your turns short, stick to your card, do not correct the
candidate, do not teach, do not switch to English, and do not mention that you are an AI. If the
candidate is silent or stuck for a while, wait patiently or repeat your last question simply."""


def partner_instructions(teil: int, content: dict, hidden: dict) -> str:
    if teil == 1:
        facts = "\n".join(f"- {card} {answer}" for card, answer in hidden["partner_facts"].items())
        cards = ", ".join(hidden["partner_cards"])
        return f"""{_PARTNER_RULES}

Task (Teil 1, Fragen zur Person): you are {hidden['partner_name']}. The candidate has four cards
({', '.join(content['cards'])}) and asks you four questions with them first. Answer each question
in 2-3 short sentences, using these facts about yourself:
{facts}
After the candidate has asked their four questions (or says they are finished), it is your turn:
ask the candidate four questions, one at a time, using your cards: {cards}. Turn each keyword
into a natural question (e.g. 'Hobby?' -> 'Was ist dein Hobby?'), wait for the answer, react
very briefly ('Aha, schön.'), then ask the next one. After your fourth question and the answer,
say 'Danke, das war's.'. Use 'du'. Do not start the conversation yourself; wait for the
candidate's first question."""
    if teil == 2:
        return f"""{_PARTNER_RULES}

Task (Teil 2, von sich erzählen): the candidate talks alone about their life, using a card with
the question '{content['question']}' and the prompts {', '.join(content['prompts'])}. This is a
monologue. Do not interrupt, do not ask questions, do not comment. Only when the candidate
clearly says they are finished (e.g. 'Das ist alles', 'fertig'), say 'Vielen Dank.' and nothing
else. Otherwise stay silent."""
    if content["variant"] == "termin":
        cal = "\n".join(f"- {e['start']}.00-{e['end']}.00: {e['text']}" for e in hidden["partner_calendar"])
        return f"""{_PARTNER_RULES}

Task (Teil 3, einen Termin finden): you are {hidden['partner_name']}. Situation: {content['situation']}
Day: {content['day']}. Your calendar for that day (the candidate cannot see it):
{cal}
Every hour from 7.00 to {LAST_HOUR}.00 not listed is free. You and the candidate must find a time
when you are both free. Propose times, and when the candidate proposes a time you are busy, say
no and give the reason from your calendar ('Um 14 Uhr kann ich nicht, da hole ich mein Fahrrad
ab.'). Accept a time only if it is free in your calendar. When you have agreed, confirm it in one
sentence. Use 'du'. Start the conversation with a short greeting and a first question or proposal."""
    return f"""{_PARTNER_RULES}

Task (Teil 3, gemeinsam etwas planen): you are {hidden['partner_name']}. Situation: {content['situation']}
Your mind map ('{content['center']}') has these points, which the candidate cannot see:
{', '.join(hidden['partner_points'])}. The candidate has different points. Plan together: bring in
your points one by one, ask the candidate for their ideas, react to them (agree, disagree, make a
counter-proposal), and agree on a plan. Keep each turn to 1-2 sentences. Use 'du'. Start the
conversation with a short greeting and a first idea."""


def partner_starts(teil: int) -> bool:
    """Teil 3: the partner opens. Teil 1 and 2: the candidate starts speaking."""
    return teil == 3


# --- grading -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class GradingDeps:
    teil: int
    content: dict
    hidden: dict
    checklist_items: list[str]


def checklist_items(teil: int, content: dict, hidden: dict) -> list[str]:
    """What the candidate had to cover; the grader marks each done or not."""
    if teil == 1:
        return [f"Frage zu: {c}" for c in content["cards"]] + [f"Antwort auf: {c}" for c in hidden["partner_cards"]]
    if teil == 2:
        return [content["question"], *content["prompts"]]
    if content["variant"] == "termin":
        return ["Termine vorschlagen", "auf Vorschläge reagieren (ja/nein mit Grund)", "einen gemeinsamen Termin vereinbaren"]
    return [*content["points"], "einen gemeinsamen Plan vereinbaren"]


TASK_MAX, CRITERION_MAX = 4, 3
MAX_SCORE = TASK_MAX + 2 * CRITERION_MAX


def score(grade: SprechenGradeAI) -> int:
    done = sum(item.done for item in grade.checklist)
    task = round(TASK_MAX * done / len(grade.checklist)) if grade.checklist else 0
    return task + grade.interaction.score + grade.accuracy.score


_GRADER_RULES = {
    1: """Teil 1 (Fragen zur Person): the candidate (A) asks four questions using their cards, then
answers the partner's (B) four questions. A question counts as done when it is a real,
understandable question about the card's topic. An answer counts as done when it is relevant
and roughly 2-3 sentences (one very short sentence is only partly done: mark it not done and say
so).""",
    2: """Teil 2 (von sich erzählen): the candidate talks alone about their life. Each prompt counts as
done when the candidate says something about it; the central question counts as done when the
talk as a whole answers it. 'interaction' here means coherent, connected speech.""",
    3: """Teil 3 (gemeinsam etwas planen): the candidate plans with the partner. For the checklist,
judge whether the candidate did each step or brought in each point of their card.""",
}

grader_agent = Agent(
    name="sprechen_grader",
    deps_type=GradingDeps,
    output_type=NativeOutput(SprechenGradeAI),
    instructions="""You are a fair, encouraging examiner giving feedback on a Goethe-Zertifikat A2
Sprechen task from its transcript. The transcript comes from speech recognition, so ignore
spelling, punctuation and obvious recognition slips. You cannot hear the audio: never mention
or judge pronunciation, fluency or intonation, not even as praise. Grade only the
candidate (A), not the partner (B). Interaction and accuracy are 0-3; A2 learners make mistakes,
so clear communication with some errors still earns 2.""",
)


@grader_agent.instructions
def _task_context(ctx: RunContext[GradingDeps]) -> str:
    d = ctx.deps
    items = "\n".join(f"- {i}" for i in d.checklist_items)
    return f"{_GRADER_RULES[d.teil]}\n\nCandidate's card: {d.content}\n\nChecklist, in this order:\n{items}"


@grader_agent.output_validator
def _complete_checklist(ctx: RunContext[GradingDeps], grade: SprechenGradeAI) -> SprechenGradeAI:
    expected = ctx.deps.checklist_items
    if [i.item for i in grade.checklist] != expected:
        raise ModelRetry(f"Return the checklist with exactly these items, in this order: {expected}")
    return grade


def format_transcript(turns: list[dict]) -> str:
    return "\n".join(f"{'A (candidate)' if t['role'] == 'candidate' else 'B (partner)'}: {t['text']}" for t in turns)
