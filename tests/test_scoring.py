import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from domain import NormalizedJob
from scoring import score
from search_profile import ConfigError, SearchProfile, load_search_profile


def job(**changes):
    values = dict(source="remoteok", source_job_id="1", title="QA Intern", url="https://example.test/job", work_mode="REMOTE", company="Acme", location="Vietnam", description="Junior QA role", employment_type="Internship", posted_at=datetime(2026, 8, 21, tzinfo=timezone.utc))
    values.update(changes)
    return NormalizedJob(**values)


def test_score_applies_each_m7_weight() -> None:
    profile = SearchProfile(required_fields=("title", "company"), include_keywords=("QA",), experience_keywords=("junior",), employment_types=("internship",), work_modes=("remote",), locations=("vietnam",), scoring_weights={"field": 25, "include": 25, "employment": 15, "workmode": 15, "experience": 10, "location": 5, "recent": 5})
    result = score(job(), profile, now=datetime(2026, 8, 22, tzinfo=timezone.utc))
    assert result.score == 100
    assert result.reasons == ("field_match: +25", "include_match: +25", "employment_match: +15", "workmode_match: +15", "location_match: +5", "experience_match: +10", "recent_match: +5")


@pytest.mark.parametrize("term", ("Junior", "Fresher", "Intern", "Entry Level", "Graduate"))
def test_config_profile_awards_experience_for_domain_roles(term: str) -> None:
    profile = load_search_profile(Path(__file__).resolve().parents[1] / "config" / "search-profile.yaml")

    result = score(job(title="QA Analyst", description=f"{term} role", posted_at=None), profile)

    assert "experience_match: +10" in result.reasons


def test_score_awards_employment_for_equivalent_part_time_separators() -> None:
    profile = SearchProfile(employment_types=("part-time",), scoring_weights={"employment": 15})

    for employment_type in ("PART_TIME", "part time"):
        result = score(job(employment_type=employment_type, posted_at=None), profile)
        assert result.score == 15
        assert result.reasons == ("employment_match: +15",)


def test_score_handles_optional_values_and_stale_posting() -> None:
    profile = SearchProfile(scoring_weights={"recent": 10, "experience": 15})
    result = score(job(title="Engineer", description=None, employment_type=None, location=None, posted_at=None), profile)
    assert result.score == 0
    assert result.reasons == ()
    stale = score(job(posted_at=datetime.now(timezone.utc) - timedelta(days=8)), profile)
    assert "recent" not in stale.reasons


def test_score_does_not_match_qa_inside_lqa_and_uses_configured_experience() -> None:
    profile = SearchProfile(include_keywords=("QA", "IT Support"), experience_keywords=("apprentice",), scoring_weights={"include": 35, "experience": 15, "recent": 0})
    false_match = score(job(title="LQA Analyst", description="Junior role", posted_at=None), profile)
    configured_match = score(job(title="IT   Support Apprentice", description=None, posted_at=None), profile)

    assert false_match.score == 0
    assert false_match.reasons == ()
    assert configured_match.score == 50
    assert configured_match.reasons == ("include_match: +35", "experience_match: +15")


def test_profile_loader_validates_threshold_and_weights(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("minimum_score: 101\n")
    with pytest.raises(ConfigError, match="minimum_score"):
        load_search_profile(profile_path)
    profile_path.write_text("scoring_weights:\n  field: 25\n  include: 25\n  employment: 15\n  workmode: 15\n  experience: 10\n  location: 5\n  recent: 4\n")
    with pytest.raises(ConfigError, match="sum to 100"):
        load_search_profile(profile_path)
    profile_path.write_text("scoring_weights:\n  field: 25\n  include: 25\n  employment: 15\n  workmode: 15\n  experience: 10\n  location: 5\n  freshness: 5\n")
    with pytest.raises(ConfigError, match="exactly"):
        load_search_profile(profile_path)


def test_score_relevance_ignores_employment_type_and_caps_only_returned_score() -> None:
    profile = SearchProfile(include_keywords=("Fresher",), scoring_weights={"include": 120, "recent": 0})
    result = score(job(title="Collections Agent", description=None, employment_type="Fresher", posted_at=None), profile)
    assert result.score == 0
    assert result.raw_score == 0
    assert result.reasons == ()


def test_score_explanation_tracks_raw_points_and_rejects_future_freshness() -> None:
    profile = SearchProfile(required_fields=("title",), include_keywords=("QA",), scoring_weights={"field": 80, "include": 80, "recent": 20})
    now = datetime(2026, 8, 21, tzinfo=timezone.utc)
    result = score(job(posted_at=now + timedelta(seconds=1)), profile, now=now)
    assert result.score == 100
    assert result.raw_score == 160
    assert result.reasons == ("field_match: +80", "include_match: +80")
    assert sum(int(reason.rsplit("+", 1)[1]) for reason in result.reasons) == result.raw_score


def test_profile_loader_rejects_empty_scoring_weights(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("scoring_weights: {}\n")
    with pytest.raises(ConfigError, match="exactly"):
        load_search_profile(profile_path)
