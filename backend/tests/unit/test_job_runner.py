import uuid

import pytest

from app.config import get_settings
from app.jobs import runner
from app.jobs.runner import JobFailed, enqueue, execute_job
from app.models import JobStatus


class JobSession:
    """Fake session holding jobs in a dict; rollback discards un-committed field changes."""

    def __init__(self, store: dict):
        self.store = store
        self.rolled_back = False

    def get(self, model, ident):
        return self.store.get(ident)

    def add(self, obj):
        obj.id = obj.id or uuid.uuid4()
        self.store[obj.id] = obj

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


@pytest.fixture
def store(monkeypatch):
    jobs: dict = {}
    monkeypatch.setattr(runner, "session_factory", lambda: JobSession(jobs))
    monkeypatch.setattr(runner.job_repo, "create_job", lambda db, job: (db.add(job), job)[1])
    monkeypatch.setattr(get_settings(), "jobs_run_inline", True)
    return jobs


@pytest.fixture
def handler(monkeypatch):
    """Register a throwaway handler for the duration of one test."""
    def register(fn):
        kind = f"test_{uuid.uuid4().hex[:8]}"
        monkeypatch.setitem(runner._handlers, kind, fn)
        return kind
    return register


def test_successful_job_stores_result(store, handler):
    kind = handler(lambda db, job: {"echo": job.input["x"]})
    job = enqueue(JobSession(store), kind, user_id=None, input={"x": 42})

    assert job.status == JobStatus.SUCCEEDED
    assert job.result == {"echo": 42}
    assert job.started_at is not None and job.finished_at is not None


def test_expected_failure_keeps_code_and_message(store, handler):
    def fail(db, job):
        raise JobFailed("budget_exceeded", "Daily budget used up")

    job = enqueue(JobSession(store), handler(fail), user_id=None, input={})
    assert job.status == JobStatus.FAILED
    assert job.error_code == "budget_exceeded"
    assert job.error_message == "Daily budget used up"


def test_crashing_handler_still_finishes_the_job(store, handler):
    def crash(db, job):
        raise KeyError("boom")

    job = enqueue(JobSession(store), handler(crash), user_id=None, input={})
    assert job.status == JobStatus.FAILED
    assert job.error_code == "internal_error"
    assert "boom" in job.error_message


def test_unknown_kind_is_rejected_before_creating_a_job(store):
    with pytest.raises(ValueError):
        enqueue(JobSession(store), "no_such_kind", user_id=None, input={})
    assert store == {}


def test_missing_job_is_logged_not_raised(store):
    execute_job(uuid.uuid4())


def test_background_mode_submits_to_executor(store, handler, monkeypatch):
    submitted = []
    monkeypatch.setattr(get_settings(), "jobs_run_inline", False)
    monkeypatch.setattr(runner, "_get_executor", lambda: type("E", (), {"submit": lambda self, *a: submitted.append(a)})())

    job = enqueue(JobSession(store), handler(lambda db, job: None), user_id=None, input={})
    assert job.status == JobStatus.PENDING
    assert submitted == [(execute_job, job.id)]


def test_reading_and_vocab_handlers_are_registered():
    import app.services.reading_service  # noqa: F401
    import app.services.vocab_extraction_service  # noqa: F401

    assert {"lesen_generate", "vocab_extraction"} <= set(runner._handlers)
