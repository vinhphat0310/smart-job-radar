"""initial schema

Revision ID: 20260821_01
Revises: None
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260821_01"
down_revision = None
branch_labels = None
depends_on = None

job_statuses = "'ACTIVE', 'CLOSED', 'EXPIRED', 'UNKNOWN'"


def _id() -> sa.Column:
    return sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True)


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    op.create_table("sources", _id(), sa.Column("name", sa.String(100), nullable=False), sa.Column("adapter_key", sa.String(100), nullable=False), sa.Column("base_url", sa.Text(), nullable=False), sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False), _created_at(), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("name", name="uq_sources_name"), sa.UniqueConstraint("adapter_key", name="uq_sources_adapter_key"))
    op.create_table("jobs", _id(), sa.Column("fingerprint", sa.String(64), nullable=False), sa.Column("title", sa.Text(), nullable=False), sa.Column("company", sa.Text()), sa.Column("location", sa.Text()), sa.Column("description", sa.Text()), sa.Column("employment_type", sa.String(50)), sa.Column("work_mode", sa.String(50)), sa.Column("experience_level", sa.String(50)), sa.Column("salary_min", sa.BigInteger()), sa.Column("salary_max", sa.BigInteger()), sa.Column("salary_currency", sa.String(3)), sa.Column("posted_at", sa.DateTime(timezone=True)), sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("current_status", sa.String(20), server_default="ACTIVE", nullable=False), _created_at(), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.CheckConstraint(f"current_status IN ({job_statuses})", name="ck_jobs_current_status"), sa.UniqueConstraint("fingerprint"))
    op.create_index("ix_jobs_current_status_last_seen_at", "jobs", ["current_status", "last_seen_at"])
    op.create_table("search_profiles", _id(), sa.Column("name", sa.String(100), nullable=False), sa.Column("config", postgresql.JSONB(), server_default="{}", nullable=False), sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False), _created_at(), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("name"))
    op.create_table("runs", _id(), sa.Column("search_profile_id", sa.BigInteger(), sa.ForeignKey("search_profiles.id", ondelete="SET NULL")), sa.Column("dry_run", sa.Boolean(), server_default="false", nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("fetched_count", sa.Integer(), server_default="0", nullable=False), sa.Column("normalized_count", sa.Integer(), server_default="0", nullable=False), sa.Column("validated_count", sa.Integer(), server_default="0", nullable=False), sa.Column("deduplicated_count", sa.Integer(), server_default="0", nullable=False), sa.Column("filtered_count", sa.Integer(), server_default="0", nullable=False), sa.Column("scored_count", sa.Integer(), server_default="0", nullable=False), sa.Column("notified_count", sa.Integer(), server_default="0", nullable=False), sa.Column("config_snapshot", postgresql.JSONB(), server_default="{}", nullable=False))
    op.create_table("job_occurrences", _id(), sa.Column("job_id", sa.BigInteger(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("source_id", sa.BigInteger(), sa.ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False), sa.Column("source_job_id", sa.String(255), nullable=False), sa.Column("url", sa.Text(), nullable=False), sa.Column("canonical_url", sa.Text(), nullable=False), sa.Column("posted_at", sa.DateTime(timezone=True)), sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), _created_at(), sa.UniqueConstraint("source_id", "source_job_id", name="uq_job_occurrences_source_job_id"), sa.UniqueConstraint("source_id", "canonical_url", name="uq_job_occurrences_source_canonical_url"))
    op.create_index("ix_job_occurrences_job_id", "job_occurrences", ["job_id"])
    op.create_table("scores", _id(), sa.Column("job_id", sa.BigInteger(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("search_profile_id", sa.BigInteger(), sa.ForeignKey("search_profiles.id", ondelete="RESTRICT"), nullable=False), sa.Column("run_id", sa.BigInteger(), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False), sa.Column("score", sa.Numeric(5, 2), nullable=False), sa.Column("passed_threshold", sa.Boolean(), nullable=False), sa.Column("explanation", postgresql.JSONB(), server_default="{}", nullable=False), _created_at(), sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_scores_score_range"), sa.UniqueConstraint("job_id", "search_profile_id", "run_id", name="uq_scores_job_profile_run"))
    op.create_index("ix_scores_search_profile_id_score", "scores", ["search_profile_id", "score"])
    op.create_table("notifications", _id(), sa.Column("job_id", sa.BigInteger(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("search_profile_id", sa.BigInteger(), sa.ForeignKey("search_profiles.id", ondelete="RESTRICT"), nullable=False), sa.Column("last_attempt_run_id", sa.BigInteger(), sa.ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False), sa.Column("channel", sa.String(30), nullable=False), sa.Column("status", sa.String(30), server_default="pending", nullable=False), sa.Column("sent_at", sa.DateTime(timezone=True)), sa.Column("error_message", sa.Text()), _created_at(), sa.CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_notifications_status"), sa.UniqueConstraint("job_id", "search_profile_id", "channel", name="uq_notifications_job_profile_channel"))
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_table("source_runs", _id(), sa.Column("run_id", sa.BigInteger(), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False), sa.Column("source_id", sa.BigInteger(), sa.ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("fetched_count", sa.Integer(), server_default="0", nullable=False), sa.Column("accepted_count", sa.Integer(), server_default="0", nullable=False), sa.Column("duration_ms", sa.Integer()), sa.Column("error_message", sa.Text()), _created_at(), sa.CheckConstraint("status IN ('OK', 'DEGRADED', 'FAILED')", name="ck_source_runs_status"), sa.UniqueConstraint("run_id", "source_id", name="uq_source_runs_run_source"))
    op.create_index("ix_source_runs_source_id", "source_runs", ["source_id"])
    op.create_table("job_status_history", _id(), sa.Column("job_id", sa.BigInteger(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("reason", sa.Text()), sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.CheckConstraint(f"status IN ({job_statuses})", name="ck_job_status_history_status"))
    op.create_index("ix_job_status_history_job_id_changed_at", "job_status_history", ["job_id", "changed_at"])


def downgrade() -> None:
    for table in ("job_status_history", "source_runs", "notifications", "scores", "job_occurrences", "runs", "search_profiles", "jobs", "sources"):
        op.drop_table(table)
