import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapters.remoteok import normalize


def test_skips_metadata_and_normalizes_job() -> None:
    payload = json.loads((Path(__file__).parent / "fixtures" / "remoteok.json").read_text())
    jobs = [job for item in payload if (job := normalize(item)) is not None]
    assert len(jobs) == 1
    job = jobs[0]
    assert (job.source, job.source_job_id, job.title, job.company) == ("remoteok", "42", "Python Engineer", "Acme")
    assert job.work_mode == "REMOTE"
    assert job.location is None
    assert (job.salary_min, job.salary_max, job.salary_currency) == (100000, 150000, "USD")
    assert job.posted_at == datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
