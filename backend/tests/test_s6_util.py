"""S6 공유 유틸 + 프롬프트 패키지 임포트 스모크 (Task 3)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.agents.s6._util import extract_json, format_section_map
from backend.agents.s6 import prompts


def test_extract_json_strips_codefence():
    assert extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_extract_json_bare_object():
    assert extract_json('잡담 {"a": 1} 끝') == '{"a": 1}'


def test_format_section_map_serializes_and_truncates():
    # remaining>200일 때만 잘린 청크를 넣는다(원본 로직).
    out = format_section_map({"Abstract": "x" * 400}, max_chars=250)
    assert "### Abstract" in out
    assert "[truncated]" in out


def test_format_section_map_full_when_under_limit():
    out = format_section_map({"Intro": "short"})
    assert out == "### Intro\nshort"


def test_prompts_split_blocks_present():
    # 설계팀은 시퀀싱 규칙(레이아웃 뇌)을, 콘텐츠팀은 가독성 규칙을 가진다.
    assert "내러티브 스파인" in prompts.SEQUENCING_RULES
    assert "compare_table" in prompts.TEMPLATE_PURPOSES
    assert "전문용어 죽이기" in prompts.WRITER_SYSTEM
    assert "레이아웃은 이미 정해졌다" in prompts.WRITER_SYSTEM
    assert "본문 텍스트는 쓰지 않는다" in prompts.ARCHITECT_SYSTEM
    # Architect 프롬프트엔 필드 마이크로포맷이 없어야 한다(레이아웃만 결정).
    assert "FieldValue 구조" not in prompts.ARCHITECT_SYSTEM


def test_monolith_helpers_delegate():
    # 모놀리식이 _util에 위임해도 기존 동작 유지.
    from backend.agents.s6_card_json import s6_agent
    assert s6_agent._extract_json('```json\n{"k": 2}\n```') == '{"k": 2}'
    assert s6_agent._format_section_map({"S": "abc"}) == "### S\nabc"
