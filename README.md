# Smart Job Radar

Python V1 for one user: Scheduler → Source Adapters → Normalizer → Validation → Deduplication → Hard Filters → Explainable Rule-based Scoring → Threshold → PostgreSQL → Telegram → Run Statistics + Source Health.

PostgreSQL on Neon is the primary database for `jobs`, `scores`, `notifications`, `runs`, and `source_runs`; SQLite is not the primary database. SQLAlchemy + psycopg are planned; Alembic is added when schema migrations begin. S3-compatible storage is outside V1 and may be considered later for files or raw data.

Keep job filters configurable; do not hard-code job criteria. Do not commit credentials, database URLs, or Telegram tokens.
