"""S2 Section Parser 단위 테스트 — LLM 호출 없음."""
from __future__ import annotations

import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

import pytest
from backend.agents.s2_parser import S2ParserAgent


@pytest.fixture
def agent() -> S2ParserAgent:
    return S2ParserAgent()


# ── regex 헬퍼 직접 테스트 ────────────────────────────────────────────────────

def test_regex_finds_introduction(agent, paper_text):
    """Introduction 섹션이 regex로 감지되어야 한다."""
    sections = agent._regex_split(paper_text)
    keys_lower = [k.lower() for k in sections]
    assert any("introduction" in k for k in keys_lower), \
        f"Introduction not found. Found: {list(sections.keys())}"


def test_regex_finds_results(agent, paper_text):
    """Results/Results and discussion 섹션이 감지되어야 한다."""
    sections = agent._regex_split(paper_text)
    keys_lower = [k.lower() for k in sections]
    assert any("result" in k for k in keys_lower), \
        f"Results not found. Found: {list(sections.keys())}"


def test_section_content_has_cellulose(agent, paper_text):
    """추출된 섹션 내용에 논문 핵심 키워드가 포함되어야 한다."""
    sections = agent._regex_split(paper_text)
    all_text = " ".join(sections.values()).lower()
    assert "cellulose" in all_text or "electrospray" in all_text


def test_regex_split_on_garbage_returns_empty(agent):
    """섹션 헤더가 없는 텍스트는 빈 dict를 반환해야 한다."""
    result = agent._regex_split("This is random text with no section headers at all.")
    assert result == {}


def test_extract_json_from_code_block(agent):
    """```json 블록에서 JSON 추출 가능해야 한다."""
    text = '```json\n{"Abstract": "hello", "Introduction": "world"}\n```'
    result = agent._extract_json(text)
    assert result == '{"Abstract": "hello", "Introduction": "world"}'


def test_extract_json_bare_braces(agent):
    """마크다운 없이 { } 로 감싼 JSON도 추출 가능해야 한다."""
    text = 'Some text before {"key": "value"} and after'
    result = agent._extract_json(text)
    assert '"key": "value"' in result


# ── execute() 통합 흐름 (LLM 없이 degraded 경로 검증) ───────────────────────

@pytest.mark.asyncio
async def test_execute_garbage_returns_degraded(agent):
    """섹션이 없는 텍스트 → degraded_mode=True."""
    from backend.core.models import S2Input
    # LLM 폴백도 실패하도록 짧은 텍스트 사용
    inp = S2Input(job_id="test-s2-deg", raw_text="no sections here", page_map={})
    out = await agent.execute(inp)
    # degraded 또는 section_map에 full_text가 있거나
    assert out.degraded_mode is True or "full_text" in out.section_map


@pytest.mark.asyncio
async def test_execute_with_paper_returns_sections(agent, paper_text):
    """실제 논문 텍스트 → section_map이 비어있지 않아야 한다 (LLM 폴백 포함)."""
    from backend.core.models import S2Input
    inp = S2Input(job_id="test-s2-paper", raw_text=paper_text, page_map={})
    out = await agent.execute(inp)
    assert len(out.section_map) > 0
    # 최소한 하나의 섹션이 실제 내용을 가져야 함
    non_empty = [v for v in out.section_map.values() if v.strip()]
    assert len(non_empty) >= 1
