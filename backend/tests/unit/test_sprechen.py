import json

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import ModelResponse, RetryPromptPart, TextPart
from pydantic_ai.models.function import FunctionModel

from app.agents import sprechen
from app.agents.core import runner
from app.agents.core.models import ModelHandle
from app.live.sprechen import merge_turns
from app.schemas.sprechen import (
    SprechenGradeAI,
    SprechenTeil1AI,
    SprechenTeil2AI,
    SprechenTeil3PlanenAI,
    SprechenTeil3TerminAI,
    common_free_hours,
)

CANDIDATE = ["Geburtstag?", "Wohnort?", "Beruf?", "Hobby?"]
PARTNER = ["Eltern?", "Musik?", "Familienname?", "Sprachen?"]


def teil1() -> dict:
    return {
        "candidate_cards": list(CANDIDATE),  # copies: tests mutate these
        "partner_cards": list(PARTNER),
        "partner_name": "Anna",
        "partner_gender": "female",
        "partner_facts": [{"card": c, "answer": f"Antwort zu {c}"} for c in CANDIDATE],
    }


def termin() -> dict:
    # Candidate free: 13. Partner free: 13, 14. So the only common free hour is 13.00.
    return {
        "situation": "Ihr Freund hat Geburtstag. Finden Sie einen Termin.",
        "day": "Samstag, 17. Mai",
        "candidate_calendar": [
            {"start": 7, "end": 10, "text": "lange schlafen"},
            {"start": 10, "end": 13, "text": "Frühstück bei Mario"},
            {"start": 14, "end": 18, "text": "Fahrrad abholen"},
            {"start": 18, "end": 22, "text": "Fußball"},
        ],
        "partner_calendar": [
            {"start": 7, "end": 11, "text": "Großeinkauf"},
            {"start": 11, "end": 12, "text": "Friseur"},
            {"start": 12, "end": 13, "text": "Essen bei Stefan"},
            {"start": 15, "end": 22, "text": "Schwimmen und Kino"},
        ],
        "partner_name": "Tom",
        "partner_gender": "male",
    }


def planen() -> dict:
    return {
        "situation": "Ihr Deutschkurs ist zu Ende. Sie planen eine Party.",
        "center": "Party",
        "candidate_points": ["Termin", "Essen", "tanzen", "Quiz", "Theater"],
        "partner_points": ["Ort", "Getränke", "Musik", "Fotos", "Einladung"],
        "partner_name": "Lea",
        "partner_gender": "female",
    }


# --- card validators ------------------------------------------------------------------------------


def test_valid_cards_pass():
    SprechenTeil1AI.model_validate(teil1())
    SprechenTeil2AI.model_validate({"question": "Was machen Sie am Wochenende?", "prompts": ["Mit wem?", "Wo?", "Sport, ...?", "Essen?"]})
    SprechenTeil3TerminAI.model_validate(termin())
    SprechenTeil3PlanenAI.model_validate(planen())


def test_teil1_partner_facts_must_cover_the_candidates_cards():
    data = teil1()
    data["partner_facts"][0]["card"] = "Alter?"
    with pytest.raises(ValidationError, match="one entry per candidate card"):
        SprechenTeil1AI.model_validate(data)


def test_teil1_cards_must_all_differ():
    data = teil1()
    data["partner_cards"][0] = "Hobby?"
    with pytest.raises(ValidationError, match="all 8 cards"):
        SprechenTeil1AI.model_validate(data)


def test_termin_calendars_share_a_free_slot():
    data = SprechenTeil3TerminAI.model_validate(termin())
    assert common_free_hours(data.candidate_calendar, data.partner_calendar) == [13]


def test_termin_without_common_free_hour_is_rejected():
    data = termin()
    data["partner_calendar"][3] = {"start": 13, "end": 22, "text": "Schwimmen und Kino"}
    data["partner_calendar"][2] = {"start": 12, "end": 13, "text": "Essen"}
    with pytest.raises(ValidationError, match="share at least one free hour"):
        SprechenTeil3TerminAI.model_validate(data)


def test_termin_with_too_much_shared_free_time_is_rejected():
    data = termin()
    data["candidate_calendar"] = data["candidate_calendar"][:2]
    data["candidate_calendar"] += [{"start": 20, "end": 21, "text": "a"}, {"start": 21, "end": 22, "text": "b"}]
    data["partner_calendar"] = [{"start": 7, "end": 8, "text": "x"}, {"start": 8, "end": 9, "text": "y"},
                                {"start": 9, "end": 10, "text": "z"}, {"start": 20, "end": 22, "text": "w"}]
    with pytest.raises(ValidationError, match="too easy"):
        SprechenTeil3TerminAI.model_validate(data)


def test_termin_rejects_overlapping_entries():
    data = termin()
    data["candidate_calendar"][1] = {"start": 9, "end": 13, "text": "Frühstück"}
    with pytest.raises(ValidationError, match="must not overlap"):
        SprechenTeil3TerminAI.model_validate(data)


def test_planen_cards_must_differ():
    data = planen()
    data["partner_points"][0] = "Essen"
    with pytest.raises(ValidationError, match="different points"):
        SprechenTeil3PlanenAI.model_validate(data)


# --- the partner's card stays hidden --------------------------------------------------------------


@pytest.mark.parametrize("split, schema, factory, secrets", [
    (sprechen.split_teil1, SprechenTeil1AI, teil1, PARTNER + ["Anna", "Antwort zu"]),
    (sprechen.split_teil3_termin, SprechenTeil3TerminAI, termin, ["Großeinkauf", "Friseur", "Tom"]),
    (sprechen.split_teil3_planen, SprechenTeil3PlanenAI, planen, ["Getränke", "Einladung", "Lea"]),
])
def test_candidate_content_never_contains_the_partners_card(split, schema, factory, secrets):
    content, hidden = split(schema.model_validate(factory()))
    dumped = json.dumps(content, ensure_ascii=False)
    assert not [s for s in secrets if s in dumped]
    assert hidden  # the live partner gets it


def test_partner_instructions_carry_the_hidden_card_and_rules():
    content, hidden = sprechen.split_teil3_termin(SprechenTeil3TerminAI.model_validate(termin()))
    text = sprechen.partner_instructions(3, content, hidden)
    assert "Großeinkauf" in text and "Samstag, 17. Mai" in text
    assert "do not correct" in text and "Start the conversation" in text
    assert sprechen.partner_starts(3) and not sprechen.partner_starts(1)


def test_teil1_partner_waits_for_the_candidate_and_uses_its_facts():
    content, hidden = sprechen.split_teil1(SprechenTeil1AI.model_validate(teil1()))
    text = sprechen.partner_instructions(1, content, hidden)
    assert "Antwort zu Wohnort?" in text and "Eltern?" in text
    assert "Do not start the conversation" in text


# --- grading ----------------------------------------------------------------------------------------


def test_checklist_items_per_teil():
    content, hidden = sprechen.split_teil1(SprechenTeil1AI.model_validate(teil1()))
    assert sprechen.checklist_items(1, content, hidden) == [f"Frage zu: {c}" for c in CANDIDATE] + [f"Antwort auf: {c}" for c in PARTNER]
    content, hidden = sprechen.split_teil3_planen(SprechenTeil3PlanenAI.model_validate(planen()))
    assert sprechen.checklist_items(3, content, hidden)[-1] == "einen gemeinsamen Plan vereinbaren"


def grade(done: list[bool], interaction=2, accuracy=1) -> dict:
    return {
        "checklist": [{"item": f"item {i}", "done": d, "comment": "c"} for i, d in enumerate(done)],
        "interaction": {"score": interaction, "comment": "ok"},
        "accuracy": {"score": accuracy, "comment": "ok"},
        "corrections": [],
        "better_phrases": ["Wo wohnst du?"],
        "summary": "Gut.",
    }


@pytest.mark.parametrize("done, expected_task", [([True] * 8, 4), ([True] * 4 + [False] * 4, 2), ([False] * 8, 0), ([True, True, False], 3)])
def test_task_score_is_computed_from_the_checklist(done, expected_task):
    assert sprechen.score(SprechenGradeAI.model_validate(grade(done))) == expected_task + 2 + 1
    assert sprechen.MAX_SCORE == 10


def test_grader_must_return_the_checklist_in_order(monkeypatch):
    monkeypatch.setattr(runner.ai_run_repo, "create_run", lambda db, run: None)
    monkeypatch.setattr(runner.ai_run_repo, "tokens_used_today", lambda db, user_id: 0)
    items = ["Frage zu: Hobby?", "Antwort auf: Musik?"]
    wrong = grade([True, False])
    right = grade([True, False])
    right["checklist"] = [{"item": i, "done": True, "comment": "c"} for i in items]
    replies, seen = [wrong, right], []

    def respond(messages, info):
        seen.append(messages[-1])
        return ModelResponse(parts=[TextPart(json.dumps(replies.pop(0)))])

    deps = sprechen.GradingDeps(teil=1, content={"cards": ["Hobby?"]}, hidden={}, checklist_items=items)
    out = runner.run_agent(None, sprechen.grader_agent, "Transcript: ...", feature="t",
                           model=ModelHandle(FunctionModel(respond), "gemini", "fake"), user_id=None, max_retries=2, deps=deps)
    assert [i.item for i in out.checklist] == items
    assert any(isinstance(p, RetryPromptPart) for p in seen[1].parts)


def test_merge_turns_joins_consecutive_same_speaker_turns_and_drops_empty_ones():
    turns = [
        {"role": "candidate", "text": " Hallo, ich habe eine Frage zum Thema Wohnort."},
        {"role": "candidate", "text": " Kannst du mir etwas dazu sagen?"},
        {"role": "partner", "text": ""},
        {"role": "partner", "text": "Ich wohne in Berlin."},
        {"role": "candidate", "text": "Schön."},
    ]
    assert merge_turns(turns) == [
        {"role": "candidate", "text": "Hallo, ich habe eine Frage zum Thema Wohnort. Kannst du mir etwas dazu sagen?"},
        {"role": "partner", "text": "Ich wohne in Berlin."},
        {"role": "candidate", "text": "Schön."},
    ]


def test_format_transcript_labels_speakers():
    assert sprechen.format_transcript([{"role": "candidate", "text": "Hallo"}, {"role": "partner", "text": "Hi"}]) == \
        "A (candidate): Hallo\nB (partner): Hi"
