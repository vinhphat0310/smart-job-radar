"""Minimal RemoteOK persistence and V1 deduplication."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
import unicodedata

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain import NormalizedJob
from models import Job, JobOccurrence, Source


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
