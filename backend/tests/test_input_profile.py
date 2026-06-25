from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.scripts.input_profile import journal_family_from_doi


def test_known_publishers():
    assert journal_family_from_doi("10.1016/j.carbpol.2024.01") == "Elsevier"
    assert journal_family_from_doi("10.1002/anie.202012345") == "Wiley"
    assert journal_family_from_doi("10.1038/s41586-024-00001") == "Nature"


def test_none_or_garbage_is_unknown():
    assert journal_family_from_doi(None) == "unknown"
    assert journal_family_from_doi("") == "unknown"
    assert journal_family_from_doi("not-a-doi") == "unknown"


def test_unknown_prefix_keeps_prefix():
    assert journal_family_from_doi("10.9999/x.y").startswith("other:10.9999")
