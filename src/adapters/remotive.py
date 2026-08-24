"""Remotive public jobs API adapter."""

from __future__ import annotations

import json
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from domain import NormalizedJob

FEED_URL = "https://remotive.com/api/remote-jobs"
USER_AGENT = "smart-job-radar/0.1 (+https://github.com/)"


class RemotiveError(RuntimeError):
    pass


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored = 0

    def handle_data(self, data: str) -> None:
        if not self._ignored:
            self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored += 1
        elif not self._ignored and tag in {"p", "br", "li", "div"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._ignored = max(0, self._ignored - 1)
        elif not self._ignored and tag in {"p", "li", "div"}:
            self.parts.append(" ")


def _text(value: Any) -> str | None:
    value = value.strip() if isinstance(value, str) else None
    return value or None


def _plain_text(value: Any) -> str | None:
    value = _text(value)
    if not value:
        return None
    parser = _PlainText()
    parser.feed(value)
    parser.close()
    return " ".join("".join(parser.parts).split()) or None


def _date(value: Any) -> datetime | None:
    value = _text(value)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _job_type(value: Any) -> str | None:
    value = _text(value)
    return value.replace("-", "_").replace(" ", "_").upper() if value else None


def normalize(item: Any) -> NormalizedJob | None:
    if not isinstance(item, dict):
        return None
    raw_id = item.get("id")
    job_id = str(raw_id).strip() if isinstance(raw_id, (str, int)) and not isinstance(raw_id, bool) else None
    title, url = _text(item.get("title")), _text(item.get("url"))
    if not job_id or not title or not url:
        return None
    return NormalizedJob(
        source="remotive", source_job_id=job_id, title=title, url=url, work_mode="REMOTE",
        company=_text(item.get("company_name")), location=_text(item.get("candidate_required_location")),
        description=_plain_text(item.get("description")), employment_type=_job_type(item.get("job_type")),
        posted_at=_date(item.get("publication_date")),
    )


class RemotiveAdapter:
    def __init__(self, timeout: float = 15) -> None:
        self.timeout = timeout

    def fetch(self) -> list[NormalizedJob]:
        request = Request(FEED_URL, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RemotiveError(f"Remotive fetch failed: {error}") from error
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise RemotiveError("Remotive returned an unexpected payload.")
        return [job for item in jobs if (job := normalize(item)) is not None]
