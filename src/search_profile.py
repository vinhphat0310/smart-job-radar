"""Configuration for deterministic job validation and filtering."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a search profile cannot be safely interpreted."""


@dataclass(frozen=True)
class SearchProfile:
    required_fields: tuple[str, ...] = ()
    include_keywords: tuple[str, ...] = ()
    exclude_keywords: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    work_modes: tuple[str, ...] = ()
    employment_types: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()


_FIELDS = tuple(SearchProfile.__dataclass_fields__)


def load_search_profile(path: str | Path) -> SearchProfile:
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"Cannot read search profile: {error}") from error
    except yaml.YAMLError as error:
        raise ConfigError(f"Invalid search profile YAML: {error}") from error
    if not isinstance(payload, dict):
        raise ConfigError("Search profile must be a YAML mapping.")
    unknown = set(payload) - set(_FIELDS)
    if unknown:
        raise ConfigError(f"Unknown search profile field: {sorted(unknown)[0]}")
    values: dict[str, tuple[str, ...]] = {}
    for name in _FIELDS:
        value = payload.get(name, [])
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise ConfigError(f"Search profile {name} must be a list of non-empty strings.")
        values[name] = tuple(item.strip() for item in value)
    return SearchProfile(**values)
