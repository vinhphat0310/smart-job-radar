"""Minimal RemoteOK persistence and V1 deduplication."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import re
import time
import unicodedata
from typing import Callable

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain import NormalizedJob
from hard_filters import apply
from models import Job, JobOccurrence, Notification, Run, Score, SearchProfile as StoredSearchProfile, Source, SourceRun
from scoring import score
from search_profile import SearchProfile
from validation import validate


class SyncError(RuntimeError):
    """Raised when PostgreSQL sync cannot be initialized."""


@dataclass
class SyncStats:
    fetched: int = 0
    new_jobs: int = 0
    new_occurrences: int = 0
    exact: int = 0
    cross_source: int = 0
    failed: int = 0


def fingerprint(company: str | None, title: str, location: str | None) -> str:
    """Return a stable V1 company/title/location fingerprint."""
    parts = (company, title, location)
    normalized = "\x1f".join(_normalize(part) for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize(value: str | None) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "").casefold()).strip()


@dataclass
class NotificationJob:
    """Minimal job payload for channel adapters."""
    title: str
    company: str | None
    location: str | None
    url: str
    score: float | int | None = None
    reasons: tuple[str, ...] = ()
    employment_type: str | None = None
    work_mode: str | None = None


@dataclass
class RunStats:
    run_id: int | None = None
    source_status: str | None = None
    fetched: int = 0
    normalized: int = 0
    validated: int = 0
    deduplicated: int = 0
    filtered: int = 0
    scored: int = 0
    qualified: int = 0
    candidates: int = 0
    sent: int = 0
    already_notified: int = 0
    send_failed: int = 0
    would_send: int = 0
    failed: int = 0


def run_remoteok(database_url: str, profile: SearchProfile, fetch: Callable[[], list[NormalizedJob]], *, notify: bool = False, dry_run: bool = False, sender: Callable[[NotificationJob], None] | None = None) -> RunStats:
    """Run RemoteOK lifecycle; notification delivery is explicit and injectable."""
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    try:
        with Session(create_engine(database_url)) as session:
            return _run_remoteok(session, profile, fetch, notify=notify, dry_run=dry_run, sender=sender)
    except SyncError:
        raise
    except (ModuleNotFoundError, SQLAlchemyError, ValueError) as error:
        raise SyncError("Could not run RemoteOK. Check DATABASE_URL and Neon access.") from error


def _run_remoteok(session: Session, profile: SearchProfile, fetch: Callable[[], list[NormalizedJob]], *, notify: bool = False, dry_run: bool = False, sender: Callable[[NotificationJob], None] | None = None) -> RunStats:
    """Persist lifecycle, then deliver eligible jobs outside the score transaction."""
    if notify and dry_run:
        raise ValueError("--notify and --dry-run cannot be used together.")
    started = time.monotonic()
    stored_profile = _profile(session, profile)
    run = Run(search_profile_id=stored_profile.id, config_snapshot=_config_snapshot(profile), dry_run=dry_run)
    source = _source(session)
    session.add(run)
    session.flush()
    source_run = SourceRun(run_id=run.id, source_id=source.id, status="OK", fetched_count=0, accepted_count=0)
    session.add(source_run)
    session.flush()
    stats = RunStats(run_id=run.id, source_status=source_run.status)
    scored_job_ids: set[int] = set()
    try:
        jobs = fetch()
        stats.fetched = len(jobs)
        stats.normalized = len(jobs)
        source_run.fetched_count = stats.fetched
        for normalized in jobs:
            if not validate(normalized).passed:
                continue
            stats.validated += 1
            try:
                with session.begin_nested():
                    job, deduplicated = _sync_job_for_run(session, source, normalized)
                    if deduplicated:
                        stats.deduplicated += 1
                    if job.id in scored_job_ids:
                        continue
                    filtered = apply(normalized, profile)
                    if not filtered.passed:
                        continue
                    stats.filtered += 1
                    result = score(normalized, profile)
                    passed_threshold = result.score >= profile.minimum_score
                    session.add(Score(
                        job_id=job.id, search_profile_id=stored_profile.id, run_id=run.id,
                        score=result.score, passed_threshold=passed_threshold,
                        explanation={"reasons": list(result.reasons), "raw_score": result.raw_score},
                    ))
                scored_job_ids.add(job.id)
                stats.scored += 1
                stats.qualified += passed_threshold
                source_run.accepted_count += 1
            except SQLAlchemyError:
                stats.failed += 1
                continue
        session.commit()
        _notify_qualified(session, run, stored_profile.id, scored_job_ids, stats, notify, dry_run, sender)
        _finish(run, source_run, stats, started, "OK")
        stats.source_status = source_run.status
        session.commit()
        return stats
    except Exception as error:
        stats.failed += 1
        _finish(run, source_run, stats, started, "FAILED", _safe_error(error))
        stats.source_status = source_run.status
        session.commit()
        raise SyncError("RemoteOK source failed.") from error


def _notify_qualified(session: Session, run: Run, profile_id: int, job_ids: set[int], stats: RunStats, notify: bool, dry_run: bool, sender: Callable[[NotificationJob], None] | None) -> None:
    """Deliver newly qualified jobs; each network attempt commits independently."""
    for job_id in job_ids:
        score_row = session.scalar(select(Score).where(Score.job_id == job_id, Score.search_profile_id == profile_id, Score.run_id == run.id))
        if score_row is None or not score_row.passed_threshold:
            continue
        stats.candidates += 1
        notification = session.scalar(select(Notification).where(Notification.job_id == job_id, Notification.search_profile_id == profile_id, Notification.channel == "telegram"))
        if notification is not None and notification.status == "sent":
            stats.already_notified += 1
            continue
        if dry_run:
            stats.would_send += 1
            continue
        if not notify:
            continue
        job = session.get(Job, job_id)
        occurrence = session.scalar(select(JobOccurrence).where(JobOccurrence.job_id == job_id))
        assert job is not None and occurrence is not None
        explanation = getattr(score_row, "explanation", None) or {}
        payload = NotificationJob(
            job.title, job.company, job.location, occurrence.url, getattr(score_row, "score", None),
            tuple(explanation.get("reasons", ())), getattr(job, "employment_type", None), getattr(job, "work_mode", None),
        )
        try:
            assert sender is not None
            sender(payload)
        except Exception as error:
            _record_notification(session, notification, job_id, profile_id, run.id, "failed", _safe_error(error))
            stats.send_failed += 1
        else:
            _record_notification(session, notification, job_id, profile_id, run.id, "sent", None)
            stats.sent += 1
        session.commit()
    run.notified_count = stats.sent


def _record_notification(session: Session, notification: Notification | None, job_id: int, profile_id: int, run_id: int, status: str, error: str | None) -> None:
    if notification is None:
        notification = Notification(job_id=job_id, search_profile_id=profile_id, last_attempt_run_id=run_id, channel="telegram", status=status)
        session.add(notification)
    notification.last_attempt_run_id = run_id
    notification.status = status
    notification.sent_at = datetime.now(timezone.utc) if status == "sent" else None
    notification.error_message = error


def _config_snapshot(profile: SearchProfile) -> dict[str, object]:
    return {name: list(value) if isinstance(value, tuple) else value for name, value in asdict(profile).items()}


def _profile(session: Session, profile: SearchProfile) -> StoredSearchProfile:
    name = "default"
    stored = session.scalar(select(StoredSearchProfile).where(StoredSearchProfile.name == name))
    snapshot = _config_snapshot(profile)
    if stored is None:
        stored = StoredSearchProfile(name=name, config=snapshot)
        session.add(stored)
        session.flush()
    elif stored.config != snapshot:
        stored.config = snapshot
    return stored


def _finish(run: Run, source_run: SourceRun, stats: RunStats, started: float, status: str, error: str | None = None) -> None:
    for name in ("fetched", "normalized", "validated", "deduplicated", "filtered", "scored"):
        setattr(run, f"{name}_count", getattr(stats, name))
    run.finished_at = datetime.now(timezone.utc)
    source_run.status = status
    source_run.duration_ms = int((time.monotonic() - started) * 1000)
    source_run.error_message = error


def _safe_error(error: Exception) -> str:
    message = str(error).replace("\n", " ")
    message = re.sub(
        r"(?i)\b(token|chat(?:_|-)?id|database(?:_|-)?url)(\s*[=:])\s*[^\s,;]+",
        lambda match: f"{match.group(1)}{match.group(2)}[redacted]", message,
    )
    message = re.sub(r"(?i)\b(?:postgres(?:ql)?(?:\+[^:]+)?|mysql|sqlite)://[^\s,;]+", "[redacted database URL]", message)
    return message[:200] or type(error).__name__


def _sync_job_for_run(session: Session, source: Source, normalized: NormalizedJob) -> tuple[Job, bool]:
    before = SyncStats()
    _sync_job(session, source, normalized, before)
    job = session.scalar(select(Job).where(Job.fingerprint == fingerprint(normalized.company, normalized.title, normalized.location)))
    assert job is not None
    return job, bool(before.exact or before.cross_source)


def sync_remoteok(database_url: str, jobs: list[NormalizedJob]) -> SyncStats:
    """Persist RemoteOK jobs; isolate individual failures with savepoints."""
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    stats = SyncStats(fetched=len(jobs))
    try:
        with Session(create_engine(database_url)) as session:
            source = _source(session)
            for normalized in jobs:
                try:
                    with session.begin_nested():
                        _sync_job(session, source, normalized, stats)
                except SQLAlchemyError:
                    stats.failed += 1
            session.commit()
    except (ModuleNotFoundError, SQLAlchemyError, ValueError) as error:
        raise SyncError("Could not sync RemoteOK jobs. Check DATABASE_URL and Neon access.") from error
    return stats


def _source(session: Session) -> Source:
    source = session.scalar(select(Source).where(Source.adapter_key == "remoteok"))
    if source is None:
        source = Source(name="RemoteOK", adapter_key="remoteok", base_url="https://remoteok.com")
        session.add(source)
        session.flush()
    return source


def _sync_job(session: Session, source: Source, normalized: NormalizedJob, stats: SyncStats) -> None:
    occurrence = session.scalar(
        select(JobOccurrence).where(
            JobOccurrence.source_id == source.id,
            JobOccurrence.source_job_id == normalized.source_job_id,
        )
    )
    if occurrence is None:
        occurrence = session.scalar(
            select(JobOccurrence).where(
                JobOccurrence.source_id == source.id,
                JobOccurrence.canonical_url == normalized.url,
            )
        )
    now = datetime.now(timezone.utc)
    if occurrence is not None:
        occurrence.fetched_at = now
        session.get(Job, occurrence.job_id).last_seen_at = now
        stats.exact += 1
        return
    key = fingerprint(normalized.company, normalized.title, normalized.location)
    job = session.scalar(select(Job).where(Job.fingerprint == key))
    if job is None:
        job = Job(
            fingerprint=key, title=normalized.title, company=normalized.company,
            location=normalized.location, description=normalized.description,
            employment_type=normalized.employment_type, work_mode=normalized.work_mode,
            salary_min=normalized.salary_min, salary_max=normalized.salary_max,
            salary_currency=normalized.salary_currency, posted_at=normalized.posted_at,
            first_seen_at=now, last_seen_at=now,
        )
        session.add(job)
        session.flush()
        stats.new_jobs += 1
    else:
        job.last_seen_at = now
        stats.cross_source += 1
    session.add(JobOccurrence(
        job_id=job.id, source_id=source.id, source_job_id=normalized.source_job_id,
        url=normalized.url, canonical_url=normalized.url, posted_at=normalized.posted_at,
        fetched_at=now,
    ))
    stats.new_occurrences += 1
