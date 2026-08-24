from contextlib import nullcontext
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from domain import NormalizedJob
from persistence import REMOTIVE_SOURCE, SyncError, _config_snapshot, _profile, _run_remoteok, _run_source
from scoring import ScoreResult
from search_profile import SearchProfile


WEIGHTS = {"field": 20, "include": 20, "employment": 10, "workmode": 10, "experience": 10, "location": 10, "recent": 20}
PROFILE = SearchProfile(required_fields=("title", "url"), include_keywords=("python",), minimum_score=90, scoring_weights=WEIGHTS)
JOB = NormalizedJob(source="remoteok", source_job_id="1", title="Python developer", url="https://example.test/1", work_mode="remote", description="python")


class FakeSession:
    def __init__(self, scalar=None):
        self.scalar_value = scalar
        self.added = []
        self.commits = 0

    def scalar(self, _query):
        return self.scalar_value

    def add(self, item):
        self.added.append(item)

    def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = len(self.added) + 100

    def begin_nested(self):
        return nullcontext()

    def commit(self):
        self.commits += 1


def test_profile_reuses_default_and_updates_config():
    stored = SimpleNamespace(id=1, config={"minimum_score": 0})
    session = FakeSession(stored)

    assert _profile(session, PROFILE) is stored
    assert stored.config == _config_snapshot(PROFILE)
    assert session.added == []


def test_run_persists_one_relation_and_below_threshold_score_once():
    session = FakeSession()
    stored = SimpleNamespace(id=11, config={})
    source = SimpleNamespace(id=12)
    job = SimpleNamespace(id=13)
    with patch("persistence._profile", return_value=stored), patch("persistence._source", return_value=source), patch("persistence._sync_job_for_run", return_value=(job, False)), patch("persistence.validate", return_value=SimpleNamespace(passed=True)), patch("persistence.apply", return_value=SimpleNamespace(passed=True)), patch("persistence.score", return_value=ScoreResult(score=40, raw_score=40, reasons=("include_match: +40",))):
        stats = _run_remoteok(session, PROFILE, lambda: [JOB, JOB])

    scores = [item for item in session.added if item.__class__.__name__ == "Score"]
    source_runs = [item for item in session.added if item.__class__.__name__ == "SourceRun"]
    runs = [item for item in session.added if item.__class__.__name__ == "Run"]
    assert len(runs) == len(source_runs) == len(scores) == 1
    assert source_runs[0].run_id == runs[0].id
    assert scores[0].passed_threshold is False
    assert scores[0].explanation["raw_score"] == scores[0].score
    assert stats.run_id == runs[0].id
    assert stats.source_status == "OK"
    assert stats.scored == 1 and stats.qualified == 0 and stats.failed == 0


def test_run_failure_closes_run_and_source_with_error_and_counters():
    session = FakeSession()
    stored = SimpleNamespace(id=11, config={})
    source = SimpleNamespace(id=12)
    with patch("persistence._profile", return_value=stored), patch("persistence._source", return_value=source):
        with pytest.raises(SyncError, match="RemoteOK source failed"):
            _run_remoteok(session, PROFILE, lambda: (_ for _ in ()).throw(RuntimeError("network\nerror")))

    run = next(item for item in session.added if item.__class__.__name__ == "Run")
    source_run = next(item for item in session.added if item.__class__.__name__ == "SourceRun")
    assert run.finished_at is not None
    assert source_run.status == "FAILED"
    assert source_run.error_message == "network error"
    assert source_run.fetched_count == 0
    assert run.fetched_count == 0 and run.scored_count == 0
    assert session.commits == 1


def test_remotive_run_uses_remotive_source_metadata_and_dry_run_never_sends():
    session = FakeSession()
    stored = SimpleNamespace(id=11, config={})
    source = SimpleNamespace(id=22)
    job = SimpleNamespace(id=13)
    with patch("persistence._profile", return_value=stored), patch("persistence._source", return_value=source) as source_helper, patch("persistence._sync_job_for_run", return_value=(job, False)), patch("persistence.validate", return_value=SimpleNamespace(passed=True)), patch("persistence.apply", return_value=SimpleNamespace(passed=True)), patch("persistence.score", return_value=ScoreResult(score=100, raw_score=100, reasons=())), patch("persistence._notify_qualified") as notify_qualified:
        stats = _run_source(session, PROFILE, REMOTIVE_SOURCE, lambda: [JOB], dry_run=True, sender=lambda _job: (_ for _ in ()).throw(AssertionError("sender called")))

    source_helper.assert_called_once_with(session, REMOTIVE_SOURCE)
    assert stats.source_status == "OK" and stats.qualified == 1 and stats.sent == 0
    assert notify_qualified.call_args.args[3] == source.id
    assert notify_qualified.call_args.args[6:8] == (False, True)
