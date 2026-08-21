import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from domain import NormalizedJob
from hard_filters import apply
import main
from search_profile import ConfigError, SearchProfile, load_search_profile
from validation import validate


def job(**changes):
    values = dict(source="remoteok", source_job_id="1", title="Marketing Manager", url="https://example.test/job", work_mode="REMOTE", company="Acme", location=None, description="Growth strategy", employment_type=None)
    values.update(changes)
    return NormalizedJob(**values)


def test_validation_requires_title_company_source_and_url_or_canonical() -> None:
    result = validate(job(title="", company="", source="", url=""))
    assert result.reasons == ("missing:title", "missing:company", "missing:source", "missing:url_or_canonical")
    assert validate(SimpleNamespace(title="Title", company="Acme", source="source", url="", canonical_url="https://example.test")).passed


def test_hard_filters_require_configured_relevance_but_allow_unknown_optional_fields() -> None:
    profile = SearchProfile(include_keywords=("IT Support", "QA"), exclude_keywords=("Sales Advisor", "Loss Prevention"), employment_types=("Part-time",))
    assert apply(job(title="IT Support Specialist", description=None, employment_type=None), profile).passed
    sales_result = apply(job(title="Sales Advisor", description="Loss Prevention", employment_type=None), profile)
    assert "excluded_keyword" in sales_result.reasons
    assert apply(job(title="QA Intern", employment_type="Internship"), profile).reasons == ("not_allowed:employment_type",)


def test_hard_filters_exclude_and_explicit_required_fields() -> None:
    profile = SearchProfile(exclude_keywords=("intern",), required_fields=("location",))
    assert apply(job(title="Marketing Intern"), profile).reasons == ("excluded_keyword", "missing_required:location")


def test_filter_remoteok_prints_rejected_reason_counts_and_examples(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    profile = SearchProfile(include_keywords=("QA",))
    jobs = [job(title="Marketing Manager"), job(title="Sales Manager", source_job_id="2"), job(title="QA Intern", source_job_id="3")]
    monkeypatch.setattr(main, "load_search_profile", lambda _: profile)
    monkeypatch.setattr(main.RemoteOKAdapter, "fetch", lambda _: jobs)
    monkeypatch.setattr(main.sys, "argv", ["main.py", "--filter-remoteok"])

    main.main()

    output = capsys.readouterr().out
    assert "fetched=3, valid=3, passed=1, rejected=2" in output
    assert "rejected: no_include_keyword=2" in output
    assert "rejected example: Marketing Manager | no_include_keyword" in output
    assert "rejected example: Sales Manager | no_include_keyword" in output


def test_profile_loader_rejects_invalid_config_and_supports_marketing_change(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("include_keywords: [Marketing]\n")
    marketing_profile = load_search_profile(profile_path)
    assert apply(job(title="Marketing Analyst"), marketing_profile).passed
    assert not apply(job(title="IT Support Specialist"), marketing_profile).passed
    profile_path.write_text("include_keywords: Marketing\n")
    with pytest.raises(ConfigError, match="include_keywords"):
        load_search_profile(profile_path)
