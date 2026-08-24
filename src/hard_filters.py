"""Deterministic configurable hard filters; no scoring or persistence."""

from dataclasses import dataclass
from typing import Any

from search_profile import SearchProfile, matches, matches_relevance


@dataclass(frozen=True)
class FilterResult:
    passed: bool
    reasons: tuple[str, ...]


def apply(job: Any, profile: SearchProfile) -> FilterResult:
    reasons = []
    if profile.include_keywords and not matches_relevance(job, profile.include_keywords):
        reasons.append("no_include_keyword")
    if profile.exclude_keywords and matches(_text(getattr(job, "title", None)), profile.exclude_keywords):
        reasons.append("excluded_keyword")
    for profile_field, job_field in (
        ("locations", "location"),
        ("work_modes", "work_mode"),
        ("employment_types", "employment_type"),
        ("sources", "source"),
    ):
        allowed = getattr(profile, profile_field)
        value = _text(getattr(job, job_field, None))
        if allowed and value and not matches(value, allowed):
            reasons.append(f"not_allowed:{job_field}")
    for field in profile.required_fields:
        if field not in {"title", "company", "source", "url", "canonical_url", "location", "description", "work_mode", "employment_type"}:
            reasons.append(f"unknown_required_field:{field}")
        elif not _text(getattr(job, field, None)):
            reasons.append(f"missing_required:{field}")
    return FilterResult(not reasons, tuple(reasons))


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
