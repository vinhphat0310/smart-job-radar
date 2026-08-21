"""SQLAlchemy schema for Smart Job Radar V1."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IdMixin:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Source(IdMixin, TimestampMixin, Base):
    __tablename__ = "sources"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_key: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    __table_args__ = (UniqueConstraint("name", name="uq_sources_name"), UniqueConstraint("adapter_key", name="uq_sources_adapter_key"))


class Job(IdMixin, TimestampMixin, Base):
    __tablename__ = "jobs"
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    employment_type: Mapped[str | None] = mapped_column(String(50))
    work_mode: Mapped[str | None] = mapped_column(String(50))
    experience_level: Mapped[str | None] = mapped_column(String(50))
    salary_min: Mapped[int | None] = mapped_column(BigInteger)
    salary_max: Mapped[int | None] = mapped_column(BigInteger)
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    current_status: Mapped[str] = mapped_column(String(20), server_default="ACTIVE", nullable=False)
    __table_args__ = (CheckConstraint("current_status IN ('ACTIVE', 'CLOSED', 'EXPIRED', 'UNKNOWN')", name="ck_jobs_current_status"), Index("ix_jobs_current_status_last_seen_at", "current_status", "last_seen_at"))


# ponytail: fingerprint is V1 dedupe; upgrade to company+title+location plus repost timing when repost matching is needed.

class JobOccurrence(IdMixin, Base):
    __tablename__ = "job_occurrences"
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False)
    source_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("source_id", "source_job_id", name="uq_job_occurrences_source_job_id"), UniqueConstraint("source_id", "canonical_url", name="uq_job_occurrences_source_canonical_url"), Index("ix_job_occurrences_job_id", "job_id"))


class SearchProfile(IdMixin, TimestampMixin, Base):
    __tablename__ = "search_profiles"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)


class Run(IdMixin, Base):
    __tablename__ = "runs"
    search_profile_id: Mapped[int | None] = mapped_column(ForeignKey("search_profiles.id", ondelete="SET NULL"))
    dry_run: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    normalized_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    validated_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    deduplicated_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    filtered_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    scored_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    notified_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}", nullable=False)


class Score(IdMixin, Base):
    __tablename__ = "scores"
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    search_profile_id: Mapped[int] = mapped_column(ForeignKey("search_profiles.id", ondelete="RESTRICT"), nullable=False)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    passed_threshold: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (CheckConstraint("score >= 0 AND score <= 100", name="ck_scores_score_range"), UniqueConstraint("job_id", "search_profile_id", "run_id", name="uq_scores_job_profile_run"), Index("ix_scores_search_profile_id_score", "search_profile_id", "score"))


class Notification(IdMixin, Base):
    __tablename__ = "notifications"
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    search_profile_id: Mapped[int] = mapped_column(ForeignKey("search_profiles.id", ondelete="RESTRICT"), nullable=False)
    last_attempt_run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), server_default="pending", nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_notifications_status"), UniqueConstraint("job_id", "search_profile_id", "channel", name="uq_notifications_job_profile_channel"), Index("ix_notifications_status", "status"))


# Retries update the same job/profile/channel notification and last_attempt_run_id; V1 has no notification_attempts table.

class SourceRun(IdMixin, Base):
    __tablename__ = "source_runs"
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    fetched_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (CheckConstraint("status IN ('OK', 'DEGRADED', 'FAILED')", name="ck_source_runs_status"), UniqueConstraint("run_id", "source_id", name="uq_source_runs_run_source"), Index("ix_source_runs_source_id", "source_id"))


class JobStatusHistory(IdMixin, Base):
    __tablename__ = "job_status_history"
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (CheckConstraint("status IN ('ACTIVE', 'CLOSED', 'EXPIRED', 'UNKNOWN')", name="ck_job_status_history_status"), Index("ix_job_status_history_job_id_changed_at", "job_id", "changed_at"))
