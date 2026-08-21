"""RemoteOK public feed adapter."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from domain import NormalizedJob

FEED_URL = "https://remoteok.com/api"
USER_AGENT = "smart-job-radar/0.1 (+https://github.com/)"


class RemoteOKError(RuntimeError):
    pass


class RemoteOKAdapter:
    def __init__(self, timeout: float = 15) -> None:
        self.timeout = timeout

    def fetch(self) -> list[NormalizedJob]:
        request = Request(FEED_URL, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RemoteOKError(f"RemoteOK fetch failed: {error}") from error
        if not isinstance(payload, list):
            raise RemoteOKError("RemoteOK returned an unexpected payload.")
        return [job for item in payload if (job := normalize(item)) is not None]


def _text(value: Any) -> str | None:
    value = value.strip() if isinstance(value, str) else None
    return value or None


def _date(value: Any) -> datetime | None:
    value = _text(value)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _salary(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def normalize(item: Any) -> NormalizedJob | None:
    if not isinstance(item, dict):
        return None
    job_id, title = _text(item.get("id")), _text(item.get("position"))
    url = _text(item.get("url")) or _text(item.get("apply_url"))
    if not job_id or not title or not url:
        return None
    tags = item.get("tags")
    location = _text(item.get("location"))
    remote = item.get("remote") is True or (isinstance(tags, list) and any(str(tag).lower() == "remote" for tag in tags))
    salary_currency = _text(item.get("currency"))
    return NormalizedJob(
        source="remoteok",
        source_job_id=job_id,
        title=title,
        url=url,
        work_mode="REMOTE" if remote or not location else "UNKNOWN",
        company=_text(item.get("company")),
        location=location,
        description=_text(item.get("description")),
        employment_type=_text(item.get("employment_type")),
        posted_at=_date(item.get("date")),
        salary_min=_salary(item.get("salary_min")),
        salary_max=_salary(item.get("salary_max")),
        salary_currency=salary_currency.upper() if salary_currency else None,
    )
