import copy

import pytest
from pydantic import ValidationError

from app.schemas.ai_outputs import (
    ReadingTeil1AIOutput,
    ReadingTeil2AIOutput,
    ReadingTeil3AIOutput,
    ReadingTeil4AIOutput,
)

BEISPIEL_MC = {"prompt": "Beispiel", "options": ["a", "b", "c"], "correct_option_index": 0, "explanation": "weil"}


def _paragraphs_and_questions() -> dict:
    return {
        "beispiel": BEISPIEL_MC,
        "paragraphs": [{"paragraph_number": n, "text": f"Absatz {n}"} for n in range(1, 6)],
        "questions": [
            {
                "question_number": n,
                "paragraph_number": n,
                "prompt": f"Frage {n}",
                "options": ["a", "b", "c"],
                "correct_option_index": 1,
                "explanation": "weil",
            }
            for n in range(1, 6)
        ],
    }


def teil1() -> dict:
    return {"article_title": "Titel", **_paragraphs_and_questions()}


def teil3() -> dict:
    return {
        "email_subject": "Hallo",
        "email_sender_name": "Gülcan",
        "greeting": "Liebe Sonja,",
        "closing_phrase": "Bis dann",
        **_paragraphs_and_questions(),
    }


FLOORS = ["EG", "1. Stock", "2. Stock", "3. Stock", "4. Stock", "UG"]


def teil2() -> dict:
    return {
        "groups": [{"floor": f, "items": [f"Ding {i}" for i in range(10)]} for f in FLOORS],
        "beispiel": {"prompt": "B", "option_a": "EG", "option_b": "UG", "correct_option_index": 0, "explanation": "w"},
        "aufgaben": [
            {
                "aufgabe_number": n,
                "prompt": f"A {n}",
                "option_a": "1. Stock",
                "option_b": "2. Stock",
                "correct_option_index": 2,
                "explanation": "w",
            }
            for n in range(1, 6)
        ],
    }


def teil4() -> dict:
    return {
        "ads": [{"code": c, "url": f"www.{c}.de", "text": f"Anzeige {c}"} for c in "abcdef"],
        "beispiel": {"prompt": "B", "correct_ad_code": "f", "explanation": "w"},
        "aufgaben": [
            {"aufgabe_number": n, "prompt": f"A {n}", "correct_ad_code": code, "explanation": "w"}
            for n, code in zip(range(1, 6), ["a", "b", "c", "d", "X"])
        ],
    }


@pytest.mark.parametrize(
    "schema, factory",
    [
        (ReadingTeil1AIOutput, teil1),
        (ReadingTeil2AIOutput, teil2),
        (ReadingTeil3AIOutput, teil3),
        (ReadingTeil4AIOutput, teil4),
    ],
)
def test_valid_output_passes(schema, factory):
    schema.model_validate(factory())


@pytest.mark.parametrize("schema, factory", [(ReadingTeil1AIOutput, teil1), (ReadingTeil3AIOutput, teil3)])
def test_paragraph_teils_reject_two_questions_on_same_paragraph(schema, factory):
    data = factory()
    data["questions"][1]["paragraph_number"] = 1
    with pytest.raises(ValidationError, match="distinct paragraph"):
        schema.model_validate(data)


@pytest.mark.parametrize("schema, factory", [(ReadingTeil1AIOutput, teil1), (ReadingTeil3AIOutput, teil3)])
def test_paragraph_teils_reject_duplicate_question_numbers(schema, factory):
    data = factory()
    data["questions"][1]["question_number"] = 1
    with pytest.raises(ValidationError, match="questions must be numbered"):
        schema.model_validate(data)


def test_teil1_rejects_wrong_option_count():
    data = teil1()
    data["questions"][0]["options"] = ["a", "b"]
    with pytest.raises(ValidationError):
        ReadingTeil1AIOutput.model_validate(data)


def test_teil2_rejects_duplicate_floor_names():
    data = teil2()
    data["groups"][1]["floor"] = "EG"
    with pytest.raises(ValidationError, match="6 distinct floor"):
        ReadingTeil2AIOutput.model_validate(data)


def test_teil2_rejects_same_floor_for_both_options():
    data = teil2()
    data["aufgaben"][0]["option_b"] = "1. Stock"
    with pytest.raises(ValidationError, match="two different floors"):
        ReadingTeil2AIOutput.model_validate(data)


def test_teil2_rejects_option_not_in_groups():
    data = teil2()
    data["beispiel"]["option_a"] = "Dach"
    with pytest.raises(ValidationError, match="floor names from groups"):
        ReadingTeil2AIOutput.model_validate(data)


def test_teil4_rejects_missing_x():
    data = teil4()
    data["aufgaben"][4]["correct_ad_code"] = "e"
    with pytest.raises(ValidationError, match="exactly one aufgabe"):
        ReadingTeil4AIOutput.model_validate(data)


def test_teil4_rejects_two_x():
    data = teil4()
    data["aufgaben"][3]["correct_ad_code"] = "X"
    with pytest.raises(ValidationError, match="exactly one aufgabe"):
        ReadingTeil4AIOutput.model_validate(data)


def test_teil4_rejects_reused_ad():
    data = teil4()
    data["aufgaben"][1]["correct_ad_code"] = "a"
    with pytest.raises(ValidationError, match="at most one aufgabe"):
        ReadingTeil4AIOutput.model_validate(data)


def test_teil4_rejects_beispiel_ad_reused_by_aufgabe():
    data = teil4()
    data["beispiel"]["correct_ad_code"] = "a"
    with pytest.raises(ValidationError, match="beispiel must not"):
        ReadingTeil4AIOutput.model_validate(data)


def test_teil4_rejects_x_as_beispiel_answer():
    data = teil4()
    data["beispiel"]["correct_ad_code"] = "X"
    with pytest.raises(ValidationError, match="real ad code, not X"):
        ReadingTeil4AIOutput.model_validate(data)


def test_teil4_rejects_unknown_ad_code():
    data = copy.deepcopy(teil4())
    data["aufgaben"][0]["correct_ad_code"] = "z"
    with pytest.raises(ValidationError, match="real ad code or 'X'"):
        ReadingTeil4AIOutput.model_validate(data)
