import io
import json
import wave

import numpy as np
import pytest
from pydantic import ValidationError
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from app.agents import hoeren
from app.agents.core import runner
from app.agents.core.checked import RunContext, generate_checked
from app.agents.core.models import ModelHandle
from app.audio.mixing import Line, assign_voices, render_script, resample
from app.audio.tts import Clip
from app.schemas.hoeren import (
    HoerenTeil1AIOutput,
    HoerenTeil2AIOutput,
    HoerenTeil3AIOutput,
    HoerenTeil4AIOutput,
)

VOCAB = [{"word": w, "part_of_speech": "noun", "article": "der", "translation": t}
         for w, t in [("Termin", "appointment"), ("Bahnhof", "station"), ("Zug", "train"), ("Arzt", "doctor")]]


def line(text, speaker="Anna", gender="female"):
    return {"speaker": speaker, "gender": gender, "text": text}


def teil1() -> dict:
    return {
        "items": [
            {
                "item_number": n,
                "context": "Sie hören eine Ansage.",
                "script": [line(f"Der Zug nach Berlin fährt heute um {n} Uhr von Gleis {n}.", "Ansage")],
                "prompt": "Wann fährt der Zug?",
                "options": [f"{n} Uhr", f"{n + 1} Uhr", f"{n + 2} Uhr"],
                "correct_option_index": 0,
                "explanation": f"Er fährt um {n} Uhr.",
            }
            for n in range(1, 6)
        ],
        "vocabulary": VOCAB,
    }


DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"]
ACTIVITIES = [("🏊", "schwimmen", "schwimmen"), ("🎂", "Geburtstag", "Geburtstag"), ("🛒", "einkaufen", "einkaufen"),
              ("🩺", "Arzt", "Arzt"), ("📚", "lernen", "lernen"), ("⚽", "Fußball", "Fußball"),
              ("🎬", "Kino", "Kino"), ("🍝", "kochen", "kochen"), ("🚲", "Fahrrad", "Fahrrad")]


def teil2() -> dict:
    pictures = [{"code": c, "emoji": e, "caption": cap, "keyword": kw} for c, (e, cap, kw) in zip("abcdefghi", ACTIVITIES)]
    # Monday -> a (example), Tuesday..Saturday -> b..f; g, h, i are distractors.
    said = [f"Am {day} {ACTIVITIES[i][2]} ich." for i, day in enumerate(DAYS)]
    return {
        "context": "Was macht Lena nächste Woche?",
        "script": [line(s, "Lena") if i % 2 == 0 else line(s, "Tom", "male") for i, s in enumerate(said + ["Und Kino?", "Nein, kein Kino."])],
        "beispiel": {"label": "Montag", "correct_code": "a", "explanation": "schwimmen"},
        "aufgaben": [{"aufgabe_number": n, "label": DAYS[n - 5], "correct_code": "abcdefghi"[n - 5], "explanation": "x"}
                     for n in range(6, 11)],
        "pictures": pictures,
        "vocabulary": VOCAB,
    }


def teil3() -> dict:
    return {
        "items": [
            {
                "item_number": n,
                "context": "Was kauft die Frau?",
                "script": [line("Ich brauche Äpfel und Brot."), line("Keine Milch?", "Verkäufer", "male"), line("Nein, Milch habe ich.")],
                "prompt": "Was kauft die Frau?",
                "options": [{"emoji": "🍎", "caption": "Äpfel", "keyword": "Äpfel"},
                            {"emoji": "🥛", "caption": "Milch", "keyword": "Milch"},
                            {"emoji": "🍞", "caption": "Brot", "keyword": "Brot"}],
                "correct_option_index": 0,
                "explanation": "Äpfel und Brot.",
            }
            for n in range(11, 16)
        ],
        "vocabulary": VOCAB,
    }


def teil4() -> dict:
    script = [line(f"Frage {i}?", "Moderator", "male") if i % 2 == 0 else line(f"Antwort {i}.", "Frau Berg") for i in range(12)]
    return {
        "context": "Sie hören ein Interview mit einer Köchin.",
        "script": script,
        "statements": [{"number": n, "statement": f"Aussage {n}", "answer": "ja" if n % 2 else "nein", "explanation": "x"}
                       for n in range(16, 21)],
        "vocabulary": VOCAB,
    }


# --- validators ----------------------------------------------------------------------------


@pytest.mark.parametrize("schema, factory", [(HoerenTeil1AIOutput, teil1), (HoerenTeil2AIOutput, teil2),
                                             (HoerenTeil3AIOutput, teil3), (HoerenTeil4AIOutput, teil4)])
def test_valid_outputs_pass(schema, factory):
    schema.model_validate(factory())


def test_teil2_rejects_a_picture_used_twice():
    data = teil2()
    data["aufgaben"][0]["correct_code"] = "a"  # already the Beispiel's answer
    with pytest.raises(ValidationError, match="only once"):
        HoerenTeil2AIOutput.model_validate(data)


def test_teil2_rejects_labels_never_said():
    data = teil2()
    data["aufgaben"][4]["label"] = "Sonntag"
    with pytest.raises(ValidationError, match="never said"):
        HoerenTeil2AIOutput.model_validate(data)


def test_teil2_rejects_correct_picture_whose_keyword_is_not_heard():
    data = teil2()
    data["pictures"][1]["keyword"] = "Spaghetti"  # b answers Aufgabe 6, but "Spaghetti" is never said
    with pytest.raises(ValidationError, match="keyword of each correct picture"):
        HoerenTeil2AIOutput.model_validate(data)


def test_teil2_requires_codes_a_to_i():
    data = teil2()
    data["pictures"][8]["code"] = "z"
    with pytest.raises(ValidationError, match="codes"):
        HoerenTeil2AIOutput.model_validate(data)


def test_teil3_requires_every_option_to_be_mentioned():
    data = teil3()
    data["items"][2]["options"][1]["keyword"] = "Käse"
    with pytest.raises(ValidationError, match="item 13: every option must be mentioned"):
        HoerenTeil3AIOutput.model_validate(data)


def test_teil4_needs_both_ja_and_nein():
    data = teil4()
    for s in data["statements"]:
        s["answer"] = "ja"
    with pytest.raises(ValidationError, match="both"):
        HoerenTeil4AIOutput.model_validate(data)


def test_picture_emoji_must_not_be_text():
    data = teil3()
    data["items"][0]["options"][0]["emoji"] = "apple"
    with pytest.raises(ValidationError, match="emoji"):
        HoerenTeil3AIOutput.model_validate(data)


# --- splits ---------------------------------------------------------------------------------


@pytest.mark.parametrize("teil, schema, factory", [(1, HoerenTeil1AIOutput, teil1), (2, HoerenTeil2AIOutput, teil2),
                                                   (3, HoerenTeil3AIOutput, teil3), (4, HoerenTeil4AIOutput, teil4)])
def test_student_content_never_contains_the_script_or_answers(teil, schema, factory):
    out = schema.model_validate(factory())
    content, key = hoeren.SPECS[teil].split(out)
    scored = {k: v for k, v in content.items() if k != "beispiel"}  # the Beispiel is shown solved
    dumped = json.dumps(scored, ensure_ascii=False)
    for segment in hoeren.scripts(out).values():
        assert all(line.text not in dumped for line in segment)
    assert "correct" not in dumped and "explanation" not in dumped and "answer" not in dumped
    assert set(key) == {"answers", "explanations", "transcripts", "vocabulary"}
    assert set(key["transcripts"]) == set(hoeren.scripts(out))


def test_teil2_beispiel_is_shown_solved_but_aufgaben_are_not():
    content, key = hoeren.split_teil2(HoerenTeil2AIOutput.model_validate(teil2()))
    assert content["beispiel"]["correct_code"] == "a"
    assert all("correct_code" not in a for a in content["aufgaben"])
    assert key["answers"] == {"6": "b", "7": "c", "8": "d", "9": "e", "10": "f"}


def test_teil4_answers_map_to_checker_vocabulary():
    spec = hoeren.SPECS[4]
    assert spec.key_to_answer("ja") == "Ja" and spec.key_to_answer("nein") == "Nein"
    assert spec.allowed_answers == ("Ja", "Nein")


# --- audio ----------------------------------------------------------------------------------


class FakeEngine:
    name = "fake"

    def __init__(self, rate=16000):
        self.rate = rate
        self.calls = []

    def voices(self, gender):
        return ["f1", "f2"] if gender == "female" else ["m1", "m2"]

    def synthesize(self, text, voice):
        self.calls.append((text, voice))
        return Clip(np.full(self.rate // 2, 0.1, dtype=np.float32), self.rate, tokens=3)


def test_each_speaker_gets_a_distinct_voice_per_gender():
    lines = [Line("Anna", "female", "a"), Line("Tom", "male", "b"), Line("Lea", "female", "c"), Line("Anna", "female", "d")]
    assert assign_voices(lines, FakeEngine()) == {"Anna": "f1", "Tom": "m1", "Lea": "f2"}


def test_render_script_joins_lines_into_one_wav_at_the_target_rate():
    engine = FakeEngine(rate=16000)
    rendered = render_script([Line("Anna", "female", "Hallo"), Line("Tom", "male", "Tschüss")], engine,
                             sample_rate=22050, gap_s=0.5, lead_s=0.4)
    with wave.open(io.BytesIO(rendered.wav)) as w:
        assert w.getframerate() == 22050 and w.getnchannels() == 1 and w.getsampwidth() == 2
        seconds = w.getnframes() / w.getframerate()
    assert seconds == pytest.approx(0.4 + 2 * (0.5 + 0.5), abs=0.01)
    assert rendered.tokens == 6
    assert [voice for _, voice in engine.calls] == ["f1", "m1"]


def test_resample_keeps_duration():
    clip = Clip(np.sin(np.linspace(0, 100, 24000)).astype(np.float32), 24000)
    assert len(resample(clip, 22050)) == 22050


# --- checked flow with transcripts ----------------------------------------------------------


@pytest.fixture
def no_db(monkeypatch):
    monkeypatch.setattr(runner.ai_run_repo, "create_run", lambda db, run: None)
    monkeypatch.setattr(runner.ai_run_repo, "tokens_used_today", lambda db, user_id: 0)


def test_checker_gets_the_transcript_and_answers_with_ja_nein(no_db):
    seen = []

    def respond(messages, info):
        if "reviewing a Goethe-Zertifikat" in (info.instructions or ""):
            seen.append(str(messages[-1]))
            answers = [{"item_number": n, "answer": "ja" if n % 2 else "NEIN", "reason": "r"} for n in range(16, 21)]
            body = {"answers": answers, "issues": []}
        else:
            body = teil4()
        return ModelResponse(parts=[TextPart(json.dumps(body))])

    ctx = RunContext(db=None, model=ModelHandle(FunctionModel(respond), "gemini", "fake"), user_id=None, max_retries=1)
    result = generate_checked(ctx, hoeren.SPECS[4], None, "A2", max_revisions=0)

    assert result.verified
    assert "Antwort 1." in seen[0] and "transcript" in seen[0]
    assert "transcripts" not in result.content


def _max_items(schema: dict) -> list[int]:
    found = []
    if isinstance(schema, dict):
        if "maxItems" in schema:
            found.append(schema["maxItems"])
        for value in schema.values():
            found += _max_items(value)
    elif isinstance(schema, list):
        for value in schema:
            found += _max_items(value)
    return found


@pytest.mark.parametrize("schema", [HoerenTeil1AIOutput, HoerenTeil2AIOutput, HoerenTeil3AIOutput, HoerenTeil4AIOutput])
def test_schemas_sent_to_the_model_only_have_small_list_ranges(schema):
    # Gemini rejects response schemas with large list-length ranges (400 INVALID_ARGUMENT);
    # longer bounds live in the validators instead.
    assert all(n <= 9 for n in _max_items(schema.model_json_schema()))


def test_script_length_is_still_enforced_by_the_validator():
    data = teil4()
    data["script"] = data["script"][:4]
    with pytest.raises(ValidationError, match="script must have 10-40 entries"):
        HoerenTeil4AIOutput.model_validate(data)
