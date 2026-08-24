"""Small source-normalized job contract; no persistence concerns."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NormalizedJob:
    source: str
    source_job_id: str
    title: str
    url: str
    work_mode: str
    company: str | None = None
    location: str | None = None
    description: str | None = None
    employment_type: str | None = None
    posted_at: datetime | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
