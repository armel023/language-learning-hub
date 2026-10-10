import json

import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
from tests.unit.test_ai_outputs import teil1, teil4

from app.agents.core import runner
from app.agents.core.models import ModelHandle
from app.agents.core.checker import CheckedAnswer, CheckerIssue, CheckerReport, normalize_answer
from app.agents.core.checked import RunContext, UnverifiedExercise, find_problems, generate_checked
from app.agents.lesen.specs import AD_ANSWERS, OPTION_LETTERS, SPECS

TEIL1_KEY = {str(n): 1 for n in range(1, 6)}  # teil1() marks option index 1 correct everywhere
TEIL1_ANSWERS = {str(n): "B" for n in range(1, 6)}  # ...which the checker writes as letter B
TEIL4_KEY = {"1": "a", "2": "b", "3": "c", "4": "d", "5": "X"}


def report(answers: dict, issues=()) -> CheckerReport:
    return CheckerReport(
        answers=[CheckedAnswer(item_number=int(k), answer=str(v), reason="r") for k, v in answers.items()],
        issues=list(issues),
    )


# --- answer normalization ----------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, allowed, expected",
    [
        ("B", OPTION_LETTERS, "B"),
        ("b", OPTION_LETTERS, "B"),
        (' "C". ', OPTION_LETTERS, "C"),
        ("Option a", OPTION_LETTERS, "A"),
        ("B)", OPTION_LETTERS, "B"),
        ("1", OPTION_LETTERS, None),  # an index, not a letter: rejected, never guessed
        ("3", OPTION_LETTERS, None),
        ("D", OPTION_LETTERS, None),
        ("x", AD_ANSWERS, "X"),
        ("A", AD_ANSWERS, "a"),
        ("g", AD_ANSWERS, None),
    ],
)
def test_normalize_answer(raw, allowed, expected):
    assert normalize_answer(raw, allowed) == expected


# --- find_problems ---------------------------------------------------------------------


def test_agreement_has_no_problems():
    assert find_problems(SPECS[1], {"answers": TEIL1_KEY}, report(TEIL1_ANSWERS)) == []


def test_key_indexes_are_compared_as_letters():
    # Index 1 in the key is letter B; a checker answer of "A" is a real disagreement.
    [problem] = find_problems(SPECS[1], {"answers": TEIL1_KEY}, report({**TEIL1_ANSWERS, "3": "A"}))
    assert problem.startswith("Item 3")
    assert "'B' (correct_option_index 1)" in problem and "'A'" in problem


def test_unanswered_item_is_a_problem():
    answers = dict(TEIL1_ANSWERS)
    del answers["5"]
    problems = find_problems(SPECS[1], {"answers": TEIL1_KEY}, report(answers))
    assert problems == ["Item 5: the reviewer could not answer it."]


def test_teil4_codes_compare_directly():
    assert find_problems(SPECS[4], {"answers": TEIL4_KEY}, report(TEIL4_KEY)) == []
    [problem] = find_problems(SPECS[4], {"answers": TEIL4_KEY}, report({**TEIL4_KEY, "5": "e"}))
    assert "answer key says 'X'" in problem


def test_only_blocking_issues_count():
    issues = [
        CheckerIssue(item_number=2, kind="ambiguous", detail="two options fit", blocking=True),
        CheckerIssue(item_number=None, kind="other", detail="slightly long", blocking=False),
    ]
    problems = find_problems(SPECS[1], {"answers": TEIL1_KEY}, report(TEIL1_ANSWERS, issues))
    assert problems == ["Item 2 (ambiguous): two options fit"]


# --- generate_checked ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def no_db(monkeypatch):
    monkeypatch.setattr(runner.ai_run_repo, "create_run", lambda db, run: None)
    monkeypatch.setattr(runner.ai_run_repo, "tokens_used_today", lambda db, user_id: 0)


def scripted(generator_outputs: list[dict], checker_answers: list[dict]):
    """Fake model: generator and checker calls are told apart by the agent's instructions."""
    gen, chk = list(generator_outputs), list(checker_answers)
    prompts = {"generator": [], "checker": []}

    def respond(messages, info):
        if "reviewing a Goethe-Zertifikat" in (info.instructions or ""):
            prompts["checker"].append(str(messages[-1]))
            body = report(chk.pop(0)).model_dump()
        else:
            prompts["generator"].append(str(messages[-1]))
            body = gen.pop(0)
        return ModelResponse(parts=[TextPart(json.dumps(body))])

    ctx = RunContext(db=None, model=ModelHandle(FunctionModel(respond), "gemini", "fake"), user_id=None, max_retries=1)
    return ctx, prompts


def test_agreeing_checker_verifies_in_one_round():
    ctx, prompts = scripted([teil1()], [TEIL1_ANSWERS])
    result = generate_checked(ctx, SPECS[1], "Sport", "A2", max_revisions=1)

    assert result.verified
    assert result.meta() == {"verified": True, "rounds": [{"round": 0, "problems": []}]}
    assert len(prompts["generator"]) == 1


def test_checker_never_sees_the_answer_key():
    # The Beispiel is shown solved to students, so only the scored questions must stay hidden.
    draft = teil1()
    for q in draft["questions"]:
        q["explanation"] = "SECRET-EXPLANATION"
    ctx, prompts = scripted([draft], [TEIL1_ANSWERS])
    generate_checked(ctx, SPECS[1], None, "A2", max_revisions=0)

    [checker_prompt] = prompts["checker"]
    questions_part = checker_prompt.split('"questions"')[1]
    assert "SECRET-EXPLANATION" not in checker_prompt
    assert "correct_option_index" not in questions_part


def test_disagreement_triggers_revision_with_the_reviewers_reasoning():
    fixed = teil1()
    ctx, prompts = scripted([teil1(), fixed], [{**TEIL1_ANSWERS, "2": "A"}, TEIL1_ANSWERS])
    result = generate_checked(ctx, SPECS[1], None, "A2", max_revisions=1)

    assert result.verified
    assert [r["round"] for r in result.rounds] == [0, 1]
    assert result.rounds[0]["problems"] and not result.rounds[1]["problems"]
    revision_prompt = prompts["generator"][1]
    assert "previous draft" in revision_prompt and "Item 2" in revision_prompt


def test_still_disagreeing_after_revisions_is_rejected():
    ctx, _ = scripted([teil4(), teil4()], [{**TEIL4_KEY, "5": "e"}, {**TEIL4_KEY, "5": "e"}])
    with pytest.raises(UnverifiedExercise) as exc:
        generate_checked(ctx, SPECS[4], None, "A2", max_revisions=1)
    assert len(exc.value.result.rounds) == 2


def test_unverified_can_be_kept_when_verification_is_optional():
    ctx, _ = scripted([teil4()], [{**TEIL4_KEY, "1": "f"}])
    result = generate_checked(ctx, SPECS[4], None, "A2", max_revisions=0, require_verification=False)
    assert not result.verified
    assert result.answer_key["answers"] == TEIL4_KEY


@pytest.mark.parametrize("teil", [1, 2, 3, 4])
def test_every_teil_has_a_complete_spec(teil):
    spec = SPECS[teil]
    assert spec.teil == teil
    assert f"Teil {teil}" in spec.build_prompt(None, "A2")
    assert spec.answer_format


def test_out_of_range_checker_answer_is_sent_back_not_counted_as_disagreement():
    # A 1-based "3" (the failure seen with gemma3:4b) must trigger a checker retry, not a revision.
    ctx, prompts = scripted([teil1()], [{**TEIL1_ANSWERS, "4": "3"}, TEIL1_ANSWERS])
    result = generate_checked(ctx, SPECS[1], None, "A2", max_revisions=1)

    assert result.verified
    assert len(prompts["generator"]) == 1
    assert len(prompts["checker"]) == 2
    assert "'3' is not a valid answer" in prompts["checker"][1]


def test_checker_answer_variants_are_normalized_before_comparing():
    ctx, prompts = scripted([teil1()], [{"1": "b", "2": "B.", "3": '"B"', "4": "Option B", "5": "b)"}])
    assert generate_checked(ctx, SPECS[1], None, "A2", max_revisions=0).verified
    assert len(prompts["checker"]) == 1


def test_checker_must_answer_every_item():
    partial = dict(TEIL1_ANSWERS)
    del partial["5"]
    ctx, prompts = scripted([teil1()], [partial, TEIL1_ANSWERS])
    assert generate_checked(ctx, SPECS[1], None, "A2", max_revisions=0).verified
    assert "Missing: [5]" in prompts["checker"][1]


def test_checker_prompt_asks_for_letters():
    ctx, prompts = scripted([teil1()], [TEIL1_ANSWERS])
    generate_checked(ctx, SPECS[1], None, "A2", max_revisions=0)
    assert '"A" for the first option' in prompts["checker"][0]
