import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from persistence import fingerprint


def test_fingerprint_normalizes_case_unicode_and_space() -> None:
    assert fingerprint("  ACME\u00a0Inc.  ", "S\u00e9nior   Engineer", "  Việt Nam ") == fingerprint(
        "acme inc.", "se\u0301nior engineer", "việt nam"
    )


def test_fingerprint_keeps_distinct_fields_distinct() -> None:
    assert fingerprint("Acme", "Engineer", "Remote") != fingerprint("Acme", "Engineer", "Hanoi")
