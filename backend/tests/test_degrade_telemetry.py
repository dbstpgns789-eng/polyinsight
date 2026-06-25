from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.core.models import DegradeCode, DegradeEvent, HARD_CODES, S1Output, S6Output


def test_degradecode_is_str_enum_with_expected_members():
    # Python 3.10 — StrEnum(3.11) 금지, (str, Enum) 관용구. 값은 소문자 코드.
    assert DegradeCode.S1_NO_SECTIONS.value == "s1_no_sections"
    assert DegradeCode.S6_TRUNCATED.value == "s6_truncated"
    assert DegradeCode("s1_low_words") is DegradeCode.S1_LOW_WORDS  # str 비교 가능


def test_degrade_event_defaults():
    e = DegradeEvent(code=DegradeCode.S1_NO_SECTIONS)
    assert e.layout is None
    assert e.detail == ""
    e2 = DegradeEvent(code=DegradeCode.S6_SCHEMA_INVALID, layout="compare_table", detail="card 3")
    assert e2.layout == "compare_table"


def test_hard_codes_membership():
    # severity = 필드가 아니라 코드 분류(spec §4). hard 코드가 short-circuit FAIL 대상.
    assert DegradeCode.S6_TRUNCATED in HARD_CODES
    assert DegradeCode.S6_SCHEMA_INVALID in HARD_CODES
    assert DegradeCode.S6_COVERAGE_MISMATCH in HARD_CODES
    assert DegradeCode.S1_EXTRACT_FAILED in HARD_CODES
    assert DegradeCode.S1_NO_SECTIONS not in HARD_CODES   # soft


def test_outputs_have_degrade_events_default_empty():
    s1 = S1Output(raw_text="x", page_map={1: "x"}, metadata=_min_meta(), word_count=1)
    assert s1.degrade_events == []
    s6 = S6Output(card_data=_min_card_data(), critical_count=0, high_count=0)
    assert s6.degrade_events == []


def _min_meta():
    from backend.core.models import PaperMetadata
    return PaperMetadata(title=None, authors=[], year=None, doi=None)


def _min_card_data():
    from backend.core.models import CardEditorData, CardMeta, FieldValue
    fv = FieldValue(value="x")
    return CardEditorData(meta=CardMeta(org=fv, dept=fv, researcher=fv, month=fv, edition_number=fv), cards=[])
