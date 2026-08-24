from contextlib import nullcontext
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from models import Notification
from notifications.telegram import format_job_message
from persistence import NotificationJob, RunStats, _notify_qualified, _record_notification, _safe_error


class FakeSession:
    def __init__(self, values=(), jobs=None):
        self.values = iter(values)
        self.jobs = jobs or {}
        self.added = []
        self.commits = 0
        self.queries = []

    def scalar(self, query):
        self.queries.append(str(query))
        return next(self.values)

    def get(self, _model, job_id):
        return self.jobs[job_id]

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1


def _run(session, *, notify=False, dry_run=False, sender=None):
    run = SimpleNamespace(id=10, notified_count=0)
    stats = RunStats()
    _notify_qualified(session, run, 20, 2, {30}, stats, notify, dry_run, sender)
    return run, stats


def test_plain_text_formatter_handles_missing_values_and_nuls():
    message = format_job_message(SimpleNamespace(title=" Dev\x00Ops ", company=None, location=None, url="https://job.test/a\x00"))
    assert message == "New job: Dev Ops\nhttps://job.test/a"


def test_formatter_includes_persisted_score_details():
    message = format_job_message(SimpleNamespace(title="DevOps", company="Radar", location="Remote", url="https://job.test/a", score=80, reasons=("field_match: +25", "include_match: +25", "workmode_match: +15"), employment_type="Full-time", work_mode="Remote"))
    assert message == "New job: 80 | DevOps\nCompany: Radar\nLocation: Remote\nType: Full-time / Remote\nWhy: field +25; include +25; workmode +15\nhttps://job.test/a"
    assert "<" not in message and "\x00" not in message


def test_formatter_includes_generic_source():
    message = format_job_message(SimpleNamespace(title="DevOps", source="Remotive", url="https://job.test/a"))
    assert "Source: Remotive" in message


def test_nonqualified_job_is_not_candidate_or_sent():
    run, stats = _run(FakeSession([SimpleNamespace(passed_threshold=False)]), notify=True, sender=lambda _job: None)
    assert (stats.candidates, stats.sent, run.notified_count) == (0, 0, 0)


def test_default_mode_only_counts_eligible_candidates_without_sending_or_state():
    session = FakeSession([SimpleNamespace(passed_threshold=True), None])
    run, stats = _run(session)
    assert (stats.candidates, stats.sent, stats.would_send, session.added, run.notified_count) == (1, 0, 0, [], 0)


def test_dry_run_never_calls_sender_or_writes_notification_state():
    session = FakeSession([SimpleNamespace(passed_threshold=True), None])
    run, stats = _run(session, dry_run=True, sender=lambda _job: (_ for _ in ()).throw(AssertionError("sender called")))
    assert (stats.candidates, stats.would_send, stats.sent, session.added, run.notified_count) == (1, 1, 0, [], 0)


def test_already_sent_job_is_not_resent():
    sent = SimpleNamespace(status="sent")
    run, stats = _run(FakeSession([SimpleNamespace(passed_threshold=True), sent]), notify=True, sender=lambda _job: (_ for _ in ()).throw(AssertionError("sender called")))
    assert (stats.candidates, stats.already_notified, stats.sent, run.notified_count) == (1, 1, 0, 0)


def test_success_creates_sent_notification_after_sender_returns():
    session = FakeSession([SimpleNamespace(passed_threshold=True), None, SimpleNamespace(url="https://job.test/30", source_id=1), "RemoteOK"], {30: SimpleNamespace(title="Job", company=None, location=None)})
    run, stats = _run(session, notify=True, sender=lambda _job: None)
    notification = session.added[0]
    assert notification.status == "sent" and notification.sent_at is not None and notification.error_message is None
    assert (notification.job_id, notification.search_profile_id, notification.last_attempt_run_id, notification.channel) == (30, 20, 10, "telegram")
    assert (stats.sent, run.notified_count, session.commits) == (1, 1, 1)


def test_cross_source_notification_uses_current_source_occurrence_url_and_name():
    payloads = []
    remotive_occurrence = SimpleNamespace(url="https://remotive.test/jobs/30", source_id=2)
    session = FakeSession([
        SimpleNamespace(passed_threshold=True, score=100, explanation={"reasons": ("include_match: +20",)}),
        None,
        remotive_occurrence,
        "Remotive",
    ], {30: SimpleNamespace(title="Job", company="Radar", location="Remote")})

    _run(session, notify=True, sender=payloads.append)

    assert payloads == [
        NotificationJob(
            title="Job", company="Radar", location="Remote", url="https://remotive.test/jobs/30", score=100,
            reasons=("include_match: +20",), employment_type=None, work_mode=None, source="Remotive",
        )
    ]
    assert "job_occurrences.source_id" in session.queries[2]


def test_failure_creates_failed_notification_and_sanitizes_message():
    session = FakeSession([SimpleNamespace(passed_threshold=True), None, SimpleNamespace(url="https://job.test/30", source_id=1), "RemoteOK"], {30: SimpleNamespace(title="Job", company=None, location=None)})
    run, stats = _run(session, notify=True, sender=lambda _job: (_ for _ in ()).throw(RuntimeError("token=secret\nfailed")))
    notification = session.added[0]
    assert notification.status == "failed" and notification.sent_at is None and notification.last_attempt_run_id == 10
    assert notification.error_message == "token=[redacted] failed"
    assert "secret" not in notification.error_message
    assert (stats.send_failed, stats.sent, run.notified_count) == (1, 0, 0)


def test_retry_updates_existing_failed_notification_to_sent():
    notification = SimpleNamespace(status="failed", sent_at=None, error_message="old")
    session = FakeSession()
    _record_notification(session, notification, 30, 20, 10, "sent", None)
    assert notification.status == "sent" and notification.sent_at is not None and notification.error_message is None
    assert session.added == []


def test_record_failure_clears_prior_sent_time():
    notification = SimpleNamespace(status="sent", sent_at=object(), error_message=None)
    _record_notification(FakeSession(), notification, 30, 20, 10, "failed", "bad")
    assert notification.status == "failed" and notification.sent_at is None and notification.error_message == "bad"


def test_safe_error_redacts_chat_and_database_secrets():
    message = _safe_error(RuntimeError("chat_id:123 DATABASE_URL=postgresql://user:password@db.test/jobs token=secret"))
    assert "123" not in message and "password" not in message and "secret" not in message
    assert "[redacted]" in message
