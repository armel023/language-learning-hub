import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.agents.core.models import ModelHandle
from app.models import Exercise, GeneratedBy, Skill, User, VocabularyItem
from app.models.vocabulary import ExtractionStatus, PartOfSpeech
from app.repositories import vocabulary_repo
from app.schemas.ai_outputs import ExtractedVocabEntry
from app.schemas.vocab_extraction import VocabExtractionConfirmRequest
from app.services import (
    reading_service,
    scoring_service,
    study_service,
    vocab_extraction_service,
)


class FakeSession:
    """Just enough of a SQLAlchemy Session for services that only add/commit/refresh."""

    def __init__(self, get_result=None):
        self.added = []
        self.commits = 0
        self._get_result = get_result
        self.get_kwargs = None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        pass

    def get(self, model, ident, **kwargs):
        self.get_kwargs = kwargs
        return self._get_result


def make_user(session_count: int = 0) -> User:
    return User(id=uuid.uuid4(), display_name="Test", study_session_count=session_count)


def make_word(**overrides) -> VocabularyItem:
    fields = dict(
        id=uuid.uuid4(),
        word="Haus",
        translation="house",
        part_of_speech=PartOfSpeech.NOUN,
        review_count=0,
        correct_count=0,
        incorrect_hard_count=0,
        incorrect_moderate_count=0,
        study_due_at_session=None,
    )
    fields.update(overrides)
    return VocabularyItem(**fields)


# --- study_service ---------------------------------------------------------------------


@pytest.fixture
def word_lookup(monkeypatch):
    word = make_word(study_due_at_session=4)
    monkeypatch.setattr(vocabulary_repo, "get_vocabulary", lambda db, user_id, item_id: word)
    return word


def test_correct_answer_clears_due_session(word_lookup):
    study_service.record_review(FakeSession(), make_user(5), word_lookup.id, "correct")
    assert word_lookup.study_due_at_session is None
    assert word_lookup.correct_count == 1
    assert word_lookup.review_count == 1
    assert word_lookup.last_reviewed_at is not None


def test_hard_miss_is_due_next_session(word_lookup):
    study_service.record_review(FakeSession(), make_user(5), word_lookup.id, "incorrect_hard")
    assert word_lookup.study_due_at_session == 6
    assert word_lookup.incorrect_hard_count == 1


def test_moderate_miss_is_due_in_two_or_three_sessions(word_lookup):
    study_service.record_review(FakeSession(), make_user(5), word_lookup.id, "incorrect_moderate")
    assert word_lookup.study_due_at_session in (7, 8)
    assert word_lookup.incorrect_moderate_count == 1


def test_review_of_unknown_word_is_404(monkeypatch):
    monkeypatch.setattr(vocabulary_repo, "get_vocabulary", lambda db, user_id, item_id: None)
    with pytest.raises(HTTPException) as exc:
        study_service.record_review(FakeSession(), make_user(), uuid.uuid4(), "correct")
    assert exc.value.status_code == 404


def test_start_session_increments_counter_and_prioritises_due_words(monkeypatch):
    due = [make_word() for _ in range(3)]
    fill = [make_word() for _ in range(50)]
    seen_exclude = {}

    def fillable(db, user_id, exclude_ids):
        seen_exclude["ids"] = exclude_ids
        return fill

    monkeypatch.setattr(vocabulary_repo, "list_due_vocabulary", lambda db, user_id, n: due)
    monkeypatch.setattr(vocabulary_repo, "list_fillable_vocabulary", fillable)

    user = make_user(2)
    session_number, words = study_service.start_session(FakeSession(), user)

    assert session_number == 3
    assert user.study_session_count == 3
    assert len(words) == study_service.SESSION_SIZE
    assert all(w in words for w in due)
    assert seen_exclude["ids"] == {w.id for w in due}


def test_start_session_caps_at_session_size_when_many_due(monkeypatch):
    due = [make_word() for _ in range(30)]
    monkeypatch.setattr(vocabulary_repo, "list_due_vocabulary", lambda db, user_id, n: due)
    monkeypatch.setattr(
        vocabulary_repo,
        "list_fillable_vocabulary",
        lambda *a, **k: pytest.fail("should not fill when due words exceed session size"),
    )
    _, words = study_service.start_session(FakeSession(), make_user())
    assert len(words) == study_service.SESSION_SIZE
    assert len({w.id for w in words}) == study_service.SESSION_SIZE


# --- scoring_service -------------------------------------------------------------------


@pytest.fixture
def exercise():
    return Exercise(id=uuid.uuid4(), skill=Skill.LESEN, teil=1, answer_key={"answers": {"1": 0, "2": 2, "3": "X"}})


def test_score_attempt_counts_correct_answers(monkeypatch, exercise):
    monkeypatch.setattr(scoring_service.attempt_repo, "create_attempt", lambda db, attempt: attempt)
    attempt = scoring_service.score_attempt(FakeSession(), make_user(), exercise, {"1": 0, "2": 1, "3": "X"})
    assert attempt.score == 2
    assert attempt.max_score == 3
    assert attempt.is_correct_per_question == {"1": True, "2": False, "3": True}


@pytest.mark.parametrize("answers", [{"1": 0, "2": 2}, {"1": 0, "2": 2, "3": "X", "4": 1}])
def test_score_attempt_requires_exactly_one_answer_per_question(exercise, answers):
    with pytest.raises(HTTPException) as exc:
        scoring_service.score_attempt(FakeSession(), make_user(), exercise, answers)
    assert exc.value.status_code == 400


# --- vocab_extraction_service ----------------------------------------------------------


def test_chunk_text_never_splits_a_line():
    lines = [f"Wort{i}: word{i}" for i in range(2000)]
    chunks = vocab_extraction_service._chunk_text("\n".join(lines), chunk_size=500)
    assert all(len(c) <= 500 for c in chunks)
    rejoined = "\n".join(chunks).split("\n")
    assert rejoined == lines[: len(rejoined)]


def test_chunk_text_caps_number_of_chunks():
    text = "\n".join("x" * 100 for _ in range(10_000))
    assert len(vocab_extraction_service._chunk_text(text, chunk_size=200)) == vocab_extraction_service.MAX_CHUNKS


def test_dedupe_entries_ignores_case_and_whitespace_but_keeps_part_of_speech():
    def entry(word, pos):
        return ExtractedVocabEntry(word=word, part_of_speech=pos, translation="t")

    entries = [
        entry("Essen", PartOfSpeech.NOUN),
        entry(" essen ", PartOfSpeech.NOUN),
        entry("essen", PartOfSpeech.VERB),
    ]
    unique = vocab_extraction_service._dedupe_entries(entries)
    assert [(e.word, e.part_of_speech) for e in unique] == [
        ("Essen", PartOfSpeech.NOUN),
        ("essen", PartOfSpeech.VERB),
    ]


@pytest.mark.parametrize("name", ["notes", "notes.doc", "notes.exe"])
def test_resolve_file_type_rejects_unsupported(name):
    with pytest.raises(HTTPException) as exc:
        vocab_extraction_service.resolve_file_type(name)
    assert exc.value.status_code == 400


def _completed_job(user_id, **overrides):
    fields = dict(
        id=uuid.uuid4(),
        user_id=user_id,
        status=ExtractionStatus.COMPLETED,
        original_filename="a.txt",
        confirmed_at=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


CONFIRM_PAYLOAD = VocabExtractionConfirmRequest(
    entries=[ExtractedVocabEntry(word="Haus", part_of_speech=PartOfSpeech.NOUN, translation="house")]
)


def test_confirm_marks_job_confirmed_and_locks_row():
    user_id = uuid.uuid4()
    job = _completed_job(user_id)
    db = FakeSession(get_result=job)

    items = vocab_extraction_service.confirm_extraction(db, user_id, job.id, CONFIRM_PAYLOAD)

    assert len(items) == 1
    assert job.confirmed_at is not None
    assert db.get_kwargs == {"with_for_update": True}


def test_confirm_twice_is_rejected():
    user_id = uuid.uuid4()
    job = _completed_job(user_id)
    db = FakeSession(get_result=job)
    vocab_extraction_service.confirm_extraction(db, user_id, job.id, CONFIRM_PAYLOAD)

    with pytest.raises(HTTPException) as exc:
        vocab_extraction_service.confirm_extraction(db, user_id, job.id, CONFIRM_PAYLOAD)
    assert exc.value.status_code == 409


def test_confirm_into_someone_elses_deck_is_404(monkeypatch):
    user_id = uuid.uuid4()
    job = _completed_job(user_id)
    monkeypatch.setattr(vocab_extraction_service.deck_service.deck_repo, "get_deck", lambda *a: None)
    payload = CONFIRM_PAYLOAD.model_copy(update={"deck_id": uuid.uuid4()})

    with pytest.raises(HTTPException) as exc:
        vocab_extraction_service.confirm_extraction(FakeSession(get_result=job), user_id, job.id, payload)
    assert exc.value.status_code == 404
    assert job.confirmed_at is None


# --- vocabulary_repo -------------------------------------------------------------------


def test_tag_filter_does_not_join_tags():
    """A JOIN on tags returns one row per tag, duplicating cards that have several tags."""
    captured = {}

    class CapturingSession:
        def scalar(self, stmt):
            return 0

        def scalars(self, stmt):
            captured["sql"] = str(stmt.compile(dialect=postgresql.dialect()))
            return SimpleNamespace(all=lambda: [])

    vocabulary_repo.list_vocabulary(CapturingSession(), uuid.uuid4(), tag="Essen")
    assert "JOIN" not in captured["sql"].upper()
    assert "EXISTS" in captured["sql"].upper()


# --- reading_service -------------------------------------------------------------------


def test_generated_by_follows_the_actual_provider():
    def handle(provider):
        return ModelHandle(model=None, provider=provider, model_name="m")

    assert reading_service._generated_by(handle("ollama")) == GeneratedBy.AI_OLLAMA
    assert reading_service._generated_by(handle("gemini")) == GeneratedBy.AI_GEMINI


def test_score_attempt_rejects_rubric_graded_exercise():
    exercise = Exercise(id=uuid.uuid4(), skill=Skill.SCHREIBEN, teil=1, answer_key=None)
    with pytest.raises(HTTPException) as exc:
        scoring_service.score_attempt(FakeSession(), make_user(), exercise, {})
    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "skill, teil, expected",
    [(Skill.LESEN, 1, "lesen_teil1"), (Skill.HOEREN, 4, "hoeren_teil4"), (Skill.SPRECHEN, 3, "sprechen_teil3")],
)
def test_exercise_type_is_derived_from_skill_and_teil(skill, teil, expected):
    assert Exercise(skill=skill, teil=teil).exercise_type == expected
