"""Configuration for deterministic job validation, filtering, and scoring."""

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


class ConfigError(ValueError):
    """Raised when a search profile cannot be safely interpreted."""


@dataclass(frozen=True)
class SearchProfile:
    required_fields: tuple[str, ...] = ()
    include_keywords: tuple[str, ...] = ()
    exclude_keywords: tuple[str, ...] = ()
    experience_keywords: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    work_modes: tuple[str, ...] = ()
    employment_types: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    minimum_score: int = 0
    scoring_weights: dict[str, int] | None = None


_LIST_FIELDS = ("required_fields", "include_keywords", "exclude_keywords", "experience_keywords", "locations", "work_modes", "employment_types", "sources")
_WEIGHT_FIELDS = {"field", "include", "employment", "workmode", "experience", "location", "recent"}
_FIELDS = set(_LIST_FIELDS) | {"minimum_score", "scoring_weights"}


def matches(value: str, candidates: tuple[str, ...]) -> bool:
    """Match configured words or phrases without matching inside a larger word."""
    return any(
        re.search(rf"(?<!\w){_phrase_pattern(candidate)}(?!\w)", value, re.IGNORECASE)
        for candidate in candidates
    )


def _phrase_pattern(candidate: str) -> str:
    """Treat whitespace, hyphen, and underscore as equivalent phrase separators."""
    return re.escape(candidate).replace(r"\ ", r"[\s_-]+")


def matches_relevance(job: object, candidates: tuple[str, ...]) -> bool:
    """Match relevance keywords in title and description only."""
    text = " ".join(
        value.strip()
        for field in ("title", "description")
        if isinstance(value := getattr(job, field, None), str) and value.strip()
    )
    return matches(text, candidates)


def load_search_profile(path: str | Path) -> SearchProfile:
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"Cannot read search profile: {error}") from error
    except yaml.YAMLError as error:
        raise ConfigError(f"Invalid search profile YAML: {error}") from error
    if not isinstance(payload, dict):
        raise ConfigError("Search profile must be a YAML mapping.")
    unknown = set(payload) - _FIELDS
    if unknown:
        raise ConfigError(f"Unknown search profile field: {sorted(unknown)[0]}")
    values: dict[str, object] = {}
    for name in _LIST_FIELDS:
        value = payload.get(name, [])
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise ConfigError(f"Search profile {name} must be a list of non-empty strings.")
        values[name] = tuple(item.strip() for item in value)
    minimum_score = payload.get("minimum_score", 0)
    if not isinstance(minimum_score, int) or isinstance(minimum_score, bool) or not 0 <= minimum_score <= 100:
        raise ConfigError("Search profile minimum_score must be an integer from 0 to 100.")
    weights = payload.get("scoring_weights", {})
    if not isinstance(weights, dict) or not weights or set(weights) != _WEIGHT_FIELDS:
        raise ConfigError("Search profile scoring_weights must define exactly: field, include, employment, workmode, experience, location, recent.")
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in weights.values()):
        raise ConfigError("Search profile scoring_weights values must be nonnegative integers.")
    if weights and sum(weights.values()) != 100:
        raise ConfigError("Search profile scoring_weights must sum to 100.")
    values["minimum_score"] = minimum_score
    values["scoring_weights"] = dict(weights)
    return SearchProfile(**values)
