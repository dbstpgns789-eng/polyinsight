from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.agents.s1_extractor import _parse_sections


def test_bold_numbered_heading():
    text = "## **1. Introduction**\nThis is intro.\n## **2. Methods**\nThis is methods."
    sections, degraded = _parse_sections(text)
    assert not degraded
    assert "introduction" in sections
    assert "methods" in sections


def test_plain_numbered_heading():
    # bioRxiv/arXiv: bold 없는 ## 번호 헤딩. 이전에는 NO_SECTIONS 발생했던 케이스.
    text = "## 1. Introduction\nThis is intro.\n## 2. Methods\nThis is methods."
    sections, degraded = _parse_sections(text)
    assert not degraded, f"섹션 파싱 실패: {list(sections.keys())}"
    assert "introduction" in sections
    assert "methods" in sections


def test_plain_terminal_heading_no_number():
    # ChemSusChem 스타일: bold 없고 번호도 없는 ## TERMINAL 섹션.
    text = "## Introduction\nThis is intro text.\n## Results\nThis is results."
    sections, degraded = _parse_sections(text)
    assert not degraded
    assert "introduction" in sections
    assert "results" in sections


def test_plain_heading_non_terminal_skipped():
    # 저널명/제목 등 알 수 없는 plain 헤딩은 섹션으로 잡지 않는다.
    text = "## Some Random Long Journal Title\nSome content."
    sections, degraded = _parse_sections(text)
    assert degraded  # 유효 섹션 없음 -> degraded


def test_mixed_bold_and_plain_headings():
    # bold + plain 혼재 (실제 논문에서 발생).
    text = (
        "## **1. Introduction**\nIntro content.\n"
        "## 2. Methods\nMethods content.\n"
        "## **3. Results**\nResults content."
    )
    sections, degraded = _parse_sections(text)
    assert not degraded
    assert "introduction" in sections
    assert "methods" in sections
    assert "results" in sections
