"""Source-independent normalized job validation."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    reasons: tuple[str, ...]


def validate(job: Any) -> ValidationResult:
    reasons = []
    for field in ("title", "company", "source"):
        if not _text(getattr(job, field, None)):
            reasons.append(f"missing:{field}")
    if not (_text(getattr(job, "url", None)) or _text(getattr(job, "canonical_url", None))):
        reasons.append("missing:url_or_canonical")
    return ValidationResult(not reasons, tuple(reasons))


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
