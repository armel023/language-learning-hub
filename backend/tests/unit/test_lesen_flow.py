import json

import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
from tests.unit.test_ai_outputs import teil1, teil4

from app.agents.core import runner
from app.agents.core.models import ModelHandle
from app.agents.lesen.checker import CheckedAnswer, CheckerIssue, CheckerReport
from app.agents.lesen.flow import RunContext, UnverifiedExercise, find_problems, generate_checked
from app.agents.lesen.specs import SPECS

TEIL1_KEY = {str(n): 1 for n in range(1, 6)}  # teil1() marks option 1 correct everywhere
TEIL4_KEY = {"1": "a", "2": "b", "3": "c", "4": "d", "5": "X"}


def report(answers: dict, issues=()) -> CheckerReport:
    return CheckerReport(
        answers=[CheckedAnswer(item_number=int(k), answer=str(v), reason="r") for k, v in answers.items()],
        issues=list(issues),
    )


# --- find_problems ---------------------------------------------------------------------


def test_agreement_has_no_problems():
    assert find_problems({"answers": TEIL1_KEY}, report(TEIL1_KEY)) == []


def test_answer_mismatch_is_a_problem_that_names_both_answers():
    [problem] = find_problems({"answers": TEIL1_KEY}, report({**TEIL1_KEY, "3": 2}))
    assert problem.startswith("Item 3") and "1" in problem and "'2'" in problem


def test_unanswered_item_is_a_problem():
    answers = dict(TEIL1_KEY)
    del answers["5"]
    assert find_problems({"answers": TEIL1_KEY}, report(answers)) == ["Item 5: the reviewer could not answer it."]


@pytest.mark.parametrize("given", [{"5": "x"}, {"5": " X "}, {"1": "A"}, {"1": '"a"'}])
def test_teil4_codes_compare_case_and_quote_insensitively(given):
    assert find_problems({"answers": TEIL4_KEY}, report({**TEIL4_KEY, **given})) == []


def test_only_blocking_issues_count():
    issues = [
        CheckerIssue(item_number=2, kind="ambiguous", detail="two options fit", blocking=True),
        CheckerIssue(item_number=None, kind="other", detail="slightly long", blocking=False),
    ]
    assert find_problems({"answers": TEIL1_KEY}, report(TEIL1_KEY, issues)) == ["Item 2 (ambiguous): two options fit"]


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
    ctx, prompts = scripted([teil1()], [TEIL1_KEY])
    result = generate_checked(ctx, SPECS[1], "Sport", "A2", max_revisions=1)

    assert result.verified
    assert result.meta() == {"verified": True, "rounds": [{"round": 0, "problems": []}]}
    assert len(prompts["generator"]) == 1


def test_checker_never_sees_the_answer_key():
    # The Beispiel is shown solved to students, so only the scored questions must stay hidden.
    draft = teil1()
    for q in draft["questions"]:
        q["explanation"] = "SECRET-EXPLANATION"
    ctx, prompts = scripted([draft], [TEIL1_KEY])
    generate_checked(ctx, SPECS[1], None, "A2", max_revisions=0)

    [checker_prompt] = prompts["checker"]
    questions_part = checker_prompt.split('"questions"')[1]
    assert "SECRET-EXPLANATION" not in checker_prompt
    assert "correct_option_index" not in questions_part


def test_disagreement_triggers_revision_with_the_reviewers_reasoning():
    fixed = teil1()
    ctx, prompts = scripted([teil1(), fixed], [{**TEIL1_KEY, "2": 0}, TEIL1_KEY])
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
