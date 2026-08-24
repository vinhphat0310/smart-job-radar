"""Deterministic profile-driven relevance scoring; no persistence."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from search_profile import SearchProfile, matches, matches_relevance


@dataclass(frozen=True)
class ScoreResult:
    score: int
    raw_score: int
    reasons: tuple[str, ...]


def score(job: Any, profile: SearchProfile, now: datetime | None = None) -> ScoreResult:
    weights = profile.scoring_weights or {}
    text = " ".join(_text(getattr(job, field, None)) for field in ("title", "description"))
    reasons: list[str] = []
    total = 0

    def award(criterion: str) -> None:
        nonlocal total
        points = weights.get(criterion, 0)
        if points > 0:
            total += points
            reasons.append(f"{criterion}_match: +{points}")

    if profile.required_fields and all(_text(getattr(job, field, None)) for field in profile.required_fields):
        award("field")
    if profile.include_keywords and matches_relevance(job, profile.include_keywords):
        award("include")
    for name, candidates, value in (
        ("employment", profile.employment_types, _text(getattr(job, "employment_type", None))),
        ("workmode", profile.work_modes, _text(getattr(job, "work_mode", None))),
        ("location", profile.locations, _text(getattr(job, "location", None))),
    ):
        if candidates and value and matches(value, candidates):
            award(name)
    if profile.experience_keywords and matches(text, profile.experience_keywords):
        award("experience")
    posted_at = getattr(job, "posted_at", None)
    current = now or datetime.now(timezone.utc)
    if isinstance(posted_at, datetime):
        posted_at = posted_at.replace(tzinfo=timezone.utc) if posted_at.tzinfo is None else posted_at
        age = current - posted_at
        if timedelta() <= age <= timedelta(days=7):
            award("recent")
    return ScoreResult(min(100, total), total, tuple(reasons))


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
