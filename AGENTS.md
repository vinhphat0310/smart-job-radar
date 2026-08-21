You are an experienced, pragmatic software engineering AI agent. Do not over-engineer a solution when a simple one is possible. Keep edits minimal. If you want an exception to ANY rule, you MUST stop and get permission first.

# Project Overview

Smart Job Radar V1 is a Python system for one user: Scheduler → Source Adapters → Normalizer → Validation → Deduplication → Hard Filters → Explainable Rule-based Scoring → Threshold → PostgreSQL → Telegram → Run Statistics + Source Health. Prefer the smallest working end-to-end flow. Planned work is not implemented work.

Primary database: PostgreSQL on Neon, storing `jobs`, `scores`, `notifications`, `runs`, and `source_runs`; do not use SQLite as the primary database. SQLAlchemy + psycopg are planned for database access; add Alembic only when schema/migration management begins. S3-compatible storage is outside V1 and may be considered later for files or raw data.

Technology currently committed: Python. `.venv` is local-only and must never be committed. `requirements.txt` is empty; do not add dependencies without a concrete need.

# Reference

Before changing code, read `AGENTS.md`, `README.md`, `docs/development-log.md`, and source directly related to the task. For conflicts, trust: current source code → `AGENTS.md` → `README.md` → `docs/development-log.md` → plans/future descriptions.

- `src/main.py` — current executable entry point.
- `requirements.txt` — Python dependency manifest.
- `README.md` — product description.
- `docs/development-log.md` — technical progress and next steps.

Do not assume a file, module, class, function, database, API, or feature exists without checking code. Distinguish completed work, work in progress, and planned work. Keep application code in `src/`; project notes in `docs/`.

# Essential Commands

```bash
# Create/activate local environment when needed
python3 -m venv .venv
source .venv/bin/activate

# Install declared dependencies
pip install -r requirements.txt

# Run the application
python3 src/main.py

# Check whitespace errors before completion
git diff --check
```

No build, formatter, linter, test runner, clean script, development server, or shell scripts are configured. Do not claim to run or document nonexistent tooling. Add exact commands when tooling is actually added.

# Patterns

Filters must remain configurable; never hard-code IT, Remote, Part-time, Vietnam, or other job criteria. Use the standard library or existing dependencies first; new dependencies require technical justification and an update to `requirements.txt`. Do not add Web UI, AI/LLM, PostgreSQL, Redis, Kubernetes, multi-user architecture, speculative abstractions, services, or modules without a clear request.

Complete the current small end-to-end milestone before expanding scope. Each change needs a clear purpose, minimum necessary files, a real validation step, and must preserve current behavior. Handle an independent source failure without stopping the pipeline when a simple isolation is possible.

Keep secrets outside Git: never commit or expose `.env`, Telegram tokens, API keys, credentials, or secrets in source, documentation, logs, commit messages, or test data. `.env.example` may contain safe placeholder values only.

# Development Log

Use only `docs/development-log.md` for technical progress; do not delete its history or create parallel log systems. Update it briefly for a milestone start, completion, block, or material status change: date, item, status, work, checks, issue, next step.

# Commit and Pull Request Guidelines

Work on branch `VinhPhat`; check it with `git branch --show-current` before significant changes. Do not change branches, merge `main`, rebase, force-push, delete branches, commit, or push unless explicitly requested. The user decides final commit and push.

When requested, use concise Conventional Commit-style messages, e.g. `chore: initialize project structure` or `docs: add project agent guidelines`. Before reporting completion: review edited code, run applicable configured checks, run `git diff --check`, fix findings, update the development log when required, and state what was and was not verified. Do not mark a task complete when its primary flow does not run.

For a significant technical task, report changed files, validation/results, remaining work, development-log update status, next step, and a proposed commit summary and short description in Vietnamese; state the main changes and important checks briefly when useful. Pull requests should state purpose, changed behavior, validation run, and required environment variables or follow-up. Keep generated files, secrets, and local `.venv` out of commits.
