"""Per-Teil configuration for Lesen generation: what differs between the four Teile, so the
shared generate -> check -> revise flow in app.agents.core.checked handles all of them."""
from app.agents.core.checked import TeilSpec
from app.agents.lesen import generators
from app.agents.prompts import reading_teil1, reading_teil2, reading_teil3, reading_teil4
from app.schemas.ai_outputs import (
    ReadingTeil1AIOutput,
    ReadingTeil2AIOutput,
    ReadingTeil3AIOutput,
    ReadingTeil4AIOutput,
)


def _split_teil1_output(ai_output: ReadingTeil1AIOutput) -> tuple[dict, dict]:
    content = {
        "article_title": ai_output.article_title,
        "beispiel": ai_output.beispiel.model_dump(),
        "paragraphs": [p.model_dump() for p in ai_output.paragraphs],
        "questions": [
            {
                "question_number": q.question_number,
                "paragraph_number": q.paragraph_number,
                "prompt": q.prompt,
                "options": q.options,
            }
            for q in ai_output.questions
        ],
    }
    answer_key = {
        "answers": {str(q.question_number): q.correct_option_index for q in ai_output.questions},
        "explanations": {str(q.question_number): q.explanation for q in ai_output.questions},
    }
    return content, answer_key


def _split_teil4_output(ai_output: ReadingTeil4AIOutput) -> tuple[dict, dict]:
    content = {
        "ads": [ad.model_dump() for ad in ai_output.ads],
        "beispiel": {
            "prompt": ai_output.beispiel.prompt,
            "correct_ad_code": ai_output.beispiel.correct_ad_code,
            "explanation": ai_output.beispiel.explanation,
        },
        "aufgaben": [
            {"aufgabe_number": a.aufgabe_number, "prompt": a.prompt} for a in ai_output.aufgaben
        ],
    }
    answer_key = {
        "answers": {str(a.aufgabe_number): a.correct_ad_code for a in ai_output.aufgaben},
        "explanations": {str(a.aufgabe_number): a.explanation for a in ai_output.aufgaben},
    }
    return content, answer_key


def _split_teil2_output(ai_output: ReadingTeil2AIOutput) -> tuple[dict, dict]:
    def build_options(option_a: str, option_b: str) -> list[str]:
        return [option_a, option_b, "Anderer Stock"]

    content = {
        "groups": [g.model_dump() for g in ai_output.groups],
        "beispiel": {
            "prompt": ai_output.beispiel.prompt,
            "options": build_options(ai_output.beispiel.option_a, ai_output.beispiel.option_b),
            "correct_option_index": ai_output.beispiel.correct_option_index,
            "explanation": ai_output.beispiel.explanation,
        },
        "aufgaben": [
            {
                "aufgabe_number": a.aufgabe_number,
                "prompt": a.prompt,
                "options": build_options(a.option_a, a.option_b),
            }
            for a in ai_output.aufgaben
        ],
    }
    answer_key = {
        "answers": {str(a.aufgabe_number): a.correct_option_index for a in ai_output.aufgaben},
        "explanations": {str(a.aufgabe_number): a.explanation for a in ai_output.aufgaben},
    }
    return content, answer_key


def _split_teil3_output(ai_output: ReadingTeil3AIOutput) -> tuple[dict, dict]:
    content = {
        "email_subject": ai_output.email_subject,
        "email_sender_name": ai_output.email_sender_name,
        "greeting": ai_output.greeting,
        "closing_phrase": ai_output.closing_phrase,
        "beispiel": ai_output.beispiel.model_dump(),
        "paragraphs": [p.model_dump() for p in ai_output.paragraphs],
        "questions": [
            {
                "question_number": q.question_number,
                "paragraph_number": q.paragraph_number,
                "prompt": q.prompt,
                "options": q.options,
            }
            for q in ai_output.questions
        ],
    }
    answer_key = {
        "answers": {str(q.question_number): q.correct_option_index for q in ai_output.questions},
        "explanations": {str(q.question_number): q.explanation for q in ai_output.questions},
    }
    return content, answer_key


OPTION_LETTERS = ("A", "B", "C")
AD_ANSWERS = ("a", "b", "c", "d", "e", "f", "X")

_OPTION_LETTER = (
    'the letter of the correct option: "A" for the first option, "B" for the second, "C" for the third'
)


def _index_to_letter(index: int | str) -> str:
    return OPTION_LETTERS[int(index)]


SPECS: dict[int, TeilSpec] = {
    1: TeilSpec(
        teil=1,
        generator=generators.teil1_agent,
        build_prompt=reading_teil1.build_user_prompt,
        split=_split_teil1_output,
        title=lambda out, topic: out.article_title,
        answer_format=f"For each question_number, {_OPTION_LETTER}.",
        allowed_answers=OPTION_LETTERS,
        key_to_answer=_index_to_letter,
    ),
    2: TeilSpec(
        teil=2,
        generator=generators.teil2_agent,
        build_prompt=reading_teil2.build_user_prompt,
        split=_split_teil2_output,
        title=lambda out, topic: f"Im Kaufhaus: {topic}" if topic else "Im Kaufhaus",
        answer_format=(
            f"For each aufgabe_number, {_OPTION_LETTER}. The third option (\"Anderer Stock\") "
            "means the item is on a floor other than the two offered."
        ),
        allowed_answers=OPTION_LETTERS,
        key_to_answer=_index_to_letter,
    ),
    3: TeilSpec(
        teil=3,
        generator=generators.teil3_agent,
        build_prompt=reading_teil3.build_user_prompt,
        split=_split_teil3_output,
        title=lambda out, topic: out.email_subject,
        answer_format=f"For each question_number, {_OPTION_LETTER}.",
        allowed_answers=OPTION_LETTERS,
        key_to_answer=_index_to_letter,
    ),
    4: TeilSpec(
        teil=4,
        generator=generators.teil4_agent,
        build_prompt=reading_teil4.build_user_prompt,
        split=_split_teil4_output,
        title=lambda out, topic: f"Anzeigen: {topic}" if topic else "Anzeigen",
        answer_format=(
            "For each aufgabe_number, the code of the matching advertisement (\"a\"-\"f\"), "
            "or \"X\" if no advertisement satisfies every detail of the Aufgabe."
        ),
        allowed_answers=AD_ANSWERS,
        key_to_answer=str,
    ),
}
