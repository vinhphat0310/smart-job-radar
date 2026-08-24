import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapters.remotive import normalize
from hard_filters import apply
from scoring import score
from search_profile import SearchProfile


def test_normalizes_remotive_fixture_with_plain_html_and_deterministic_fields():
    payload = json.loads((Path(__file__).parent / "fixtures" / "remotive.json").read_text())
    jobs = [job for item in payload["jobs"] if (job := normalize(item)) is not None]
    assert len(jobs) == 3
    job = jobs[0]
    assert (job.source, job.source_job_id, job.work_mode, job.employment_type) == ("remotive", "123", "REMOTE", "FULL_TIME")
    assert job.description == "Build Python tools."
    assert job.posted_at == datetime(2026, 8, 24, 12, tzinfo=timezone.utc)
    assert jobs[1].posted_at is None and jobs[1].description == "Text"


def test_remotive_part_time_passes_hard_filter_and_awards_employment_score():
    payload = json.loads((Path(__file__).parent / "fixtures" / "remotive.json").read_text())
    job = normalize(payload["jobs"][3])
    profile = SearchProfile(include_keywords=("QA",), employment_types=("part-time",), scoring_weights={"include": 25, "employment": 15})

    assert job is not None and job.employment_type == "PART_TIME"
    assert apply(job, profile).passed
    assert score(job, profile).reasons == ("include_match: +25", "employment_match: +15")


def test_remotive_skips_missing_required_and_non_mapping_items():
    assert normalize({"id": "1", "title": "Missing URL"}) is None
    assert normalize([]) is None
