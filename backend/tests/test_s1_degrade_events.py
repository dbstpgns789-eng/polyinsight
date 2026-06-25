from __future__ import annotations

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.agents.s1_extractor import build_s1_degrade_events, s1_agent
from backend.core.models import DegradeCode, S1Input


def _codes(events):
    return [e.code for e in events]


def test_builder_no_degrade_when_healthy():
    ev = build_s1_degrade_events(word_count=5000, min_word_count=100,
                                 section_degraded=False, parse_fallback=False)
    assert ev == []


def test_builder_low_words_carries_detail():
    ev = build_s1_degrade_events(word_count=40, min_word_count=100,
                                 section_degraded=False, parse_fallback=False)
    assert _codes(ev) == [DegradeCode.S1_LOW_WORDS]
    assert "40" in ev[0].detail


def test_builder_no_sections():
    ev = build_s1_degrade_events(word_count=5000, min_word_count=100,
                                 section_degraded=True, parse_fallback=False)
    assert _codes(ev) == [DegradeCode.S1_NO_SECTIONS]


def test_builder_parse_fallback_and_no_sections_both():
    ev = build_s1_degrade_events(word_count=5000, min_word_count=100,
                                 section_degraded=True, parse_fallback=True)
    assert set(_codes(ev)) == {DegradeCode.S1_PARSE_FALLBACK, DegradeCode.S1_NO_SECTIONS}


def test_execute_empty_bytes_emits_extract_failed():
    # 빈 입력 = 추출 불가 = EXTRACT_FAILED (하드 코드). 실 PDF 없이 검증 가능한 경로.
    out = asyncio.run(s1_agent.execute(S1Input(job_id="t", pdf_bytes=b"")))
    assert DegradeCode.S1_EXTRACT_FAILED in _codes(out.degrade_events)
    assert out.degraded is True
