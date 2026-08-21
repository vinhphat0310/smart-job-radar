# Smart Job Radar

Python V1 for one user: Scheduler → Source Adapters → Normalizer → Validation → Deduplication → Hard Filters → Explainable Rule-based Scoring → Threshold → PostgreSQL → Telegram → Run Statistics + Source Health.

PostgreSQL on Neon is the primary database for `jobs`, `scores`, `notifications`, `runs`, and `source_runs`; SQLite is not the primary database. SQLAlchemy + psycopg are planned; Alembic is added when schema migrations begin. S3-compatible storage is outside V1 and may be considered later for files or raw data.

## RemoteOK source check

Fetch RemoteOK's public JSON feed and print normalized count plus up to three examples. This command does not write PostgreSQL or send Telegram messages:

```bash
python3 src/main.py --fetch-remoteok
```

Validate and filter the same feed with `config/search-profile.yaml`; prints fetched, valid, passed, then up to three passing examples. It does not write PostgreSQL or send Telegram messages:

```bash
python3 src/main.py --filter-remoteok
```

Sync normalized RemoteOK jobs to existing PostgreSQL schema. This writes `sources`, `jobs`, and `job_occurrences`; configure local `DATABASE_URL` first:

```bash
python3 src/main.py --sync-remoteok
```

Run tests after installing declared dependencies:

```bash
pytest
```

## Telegram test

Copy `.env.example` to `.env`, then set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. After sending `/start` to the bot, get the chat ID without printing the token:

```bash
python3 src/main.py --print-chat-id
```

Set the returned ID in `.env`, then send the test message:

```bash
python3 src/main.py
```

## Neon connection

Set `DATABASE_URL` in local `.env`, then verify PostgreSQL without printing the connection string:

```bash
python3 src/main.py --check-db
```


Apply the initial schema (writes to the configured database), then check it without changes:

```bash
alembic upgrade head
python3 src/main.py --check-schema
```

V1 deduplicates jobs by fingerprint; upgrade matching to company, title, location, and repost timing when repost handling is needed. Notification retries update the same job/profile/channel record and `last_attempt_run_id`; V1 has no notification-attempt history.

Keep job filters configurable; do not hard-code job criteria. Do not commit credentials, database URLs, or Telegram tokens.
