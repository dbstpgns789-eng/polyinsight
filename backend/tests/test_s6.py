"""S6 Card JSON Agent 테스트.

- 기본 실행: LLM 호출 없음, pytest-mock으로 완전 격리
- integration 마크: 실제 Gemini API 호출 (--run-integration 플래그 필요)

실행:
  pytest tests/test_s6.py              # mock 테스트만 (빠름, quota 소비 없음)
  pytest tests/test_s6.py -m integration  # 실제 API 호출 (하루 1회 권장)
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def agent():
    from backend.agents.s6_card_json import S6CardJsonAgent
    return S6CardJsonAgent()


# ── LLM mock 응답 픽스처 ──────────────────────────────────────────────────────

@pytest.fixture
def mock_llm_response() -> str:
    """실제 Gemini 응답과 동일한 구조의 JSON 문자열."""
    return json.dumps({
        "meta": {
            "org": {"value": "한국생산기술연구원", "confidence": "high",
                    "match_quality": "exact", "claim_type": "qualitative",
                    "source": {"section": "Abstract", "page": 1},
                    "risk_level": "LOW", "verified": True},
            "dept": {"value": "융합기술연구소", "confidence": "high",
                     "match_quality": "exact", "claim_type": "qualitative",
                     "source": {"section": "Abstract", "page": 1},
                     "risk_level": "LOW", "verified": True},
            "researcher": {"value": "이호익", "confidence": "high",
                           "match_quality": "exact", "claim_type": "qualitative",
                           "source": {"section": "Abstract", "page": 1},
                           "risk_level": "LOW", "verified": True},
            "month": {"value": "2024-01", "confidence": "high",
                      "match_quality": "exact", "claim_type": "qualitative",
                      "source": {"section": "Abstract", "page": 1},
                      "risk_level": "LOW", "verified": True},
            "edition_number": {"value": "80", "confidence": "medium",
                               "match_quality": "normalized", "claim_type": "qualitative",
                               "source": {"section": "Abstract", "page": 1},
                               "risk_level": "MEDIUM", "verified": True},
        },
        "card1": {
            "pretitle": {"value": "셀룰로오스 마이크로비드", "confidence": "high",
                         "match_quality": "exact", "claim_type": "qualitative",
                         "source": {"section": "Abstract", "page": 1},
                         "risk_level": "LOW", "verified": True},
            "title": {"value": "전기분무 기반 친환경 복합 마이크로비드 제조", "confidence": "high",
                      "match_quality": "semantic", "claim_type": "qualitative",
                      "source": {"section": "Abstract", "page": 1},
                      "risk_level": "HIGH", "verified": True},
            "mascot_bubble": {"value": "마이크로플라스틱을 대체합니다", "confidence": "medium",
                              "match_quality": "semantic", "claim_type": "qualitative",
                              "source": {"section": "Abstract", "page": 1},
                              "risk_level": "HIGH", "verified": True},
        },
        "card2": {
            "intro": {"value": "생분해성 셀룰로오스 마이크로비드로 마이크로플라스틱 문제 해결", "confidence": "high",
                      "match_quality": "exact", "claim_type": "qualitative",
                      "source": {"section": "Abstract", "page": 1},
                      "risk_level": "LOW", "verified": True},
            "keyword_line": {"value": "셀룰로오스 · 전기분무 · CON · 복합재", "confidence": "high",
                             "match_quality": "exact", "claim_type": "qualitative",
                             "source": {"section": "Abstract", "page": 1},
                             "risk_level": "LOW", "verified": True},
            "footnote": {"value": "Cellulose (2024) doi:10.1007/s10570-024-05757-4", "confidence": "high",
                         "match_quality": "exact", "claim_type": "qualitative",
                         "source": {"section": "Abstract", "page": 1},
                         "risk_level": "LOW", "verified": True},
        },
        "card3": {
            "problem": {"value": "석유계 마이크로플라스틱의 환경 오염", "confidence": "high",
                        "match_quality": "exact", "claim_type": "qualitative",
                        "source": {"section": "Introduction", "page": 2},
                        "risk_level": "LOW", "verified": True},
            "achievement": {"value": "압축강도 238 ± 18 MPa 달성", "confidence": "high",
                            "match_quality": "exact", "claim_type": "quantitative",
                            "source": {"section": "Abstract", "page": 1},
                            "risk_level": "LOW", "verified": True},
            "mascot_bubble": {"value": "강도를 높였습니다", "confidence": "medium",
                              "match_quality": "semantic", "claim_type": "qualitative",
                              "source": {"section": "Abstract", "page": 1},
                              "risk_level": "HIGH", "verified": True},
            "photo_caption": {"value": "SEM 이미지: 셀룰로오스 마이크로비드", "confidence": "medium",
                              "match_quality": "normalized", "claim_type": "qualitative",
                              "source": {"section": "Results", "page": 4},
                              "risk_level": "MEDIUM", "verified": True},
        },
        "card4": {
            "before_label": {"value": "순수 셀룰로오스 마이크로비드", "confidence": "high",
                             "match_quality": "exact", "claim_type": "qualitative",
                             "source": {"section": "Abstract", "page": 1},
                             "risk_level": "LOW", "verified": True},
            "after_label": {"value": "CON 복합 마이크로비드", "confidence": "high",
                            "match_quality": "exact", "claim_type": "qualitative",
                            "source": {"section": "Abstract", "page": 1},
                            "risk_level": "LOW", "verified": True},
            "description": {"value": "공유결합 유기 나노시트(CON) 첨가로 기계적 특성 향상", "confidence": "high",
                            "match_quality": "exact", "claim_type": "qualitative",
                            "source": {"section": "Abstract", "page": 1},
                            "risk_level": "LOW", "verified": True},
            "result": {"value": "142 MPa → 238 MPa (68% 향상)", "confidence": "high",
                       "match_quality": "normalized", "claim_type": "quantitative",
                       "source": {"section": "Abstract", "page": 1},
                       "risk_level": "MEDIUM", "verified": True},
            "mascot_bubble": {"value": "CON이 핵심입니다", "confidence": "medium",
                              "match_quality": "semantic", "claim_type": "qualitative",
                              "source": {"section": "Abstract", "page": 1},
                              "risk_level": "HIGH", "verified": True},
        },
        "card5": {
            "pre_title": {"value": "친환경 소재 연구", "confidence": "high",
                          "match_quality": "exact", "claim_type": "qualitative",
                          "source": {"section": "Conclusion", "page": 8},
                          "risk_level": "LOW", "verified": True},
            "main_title": {"value": "마이크로플라스틱, 이제 대체할 수 있습니다", "confidence": "medium",
                           "match_quality": "semantic", "claim_type": "qualitative",
                           "source": {"section": "Conclusion", "page": 8},
                           "risk_level": "HIGH", "verified": True},
            "cta": {"value": "KITECH 연구팀에 문의하세요", "confidence": "medium",
                    "match_quality": "semantic", "claim_type": "qualitative",
                    "source": {"section": "Conclusion", "page": 8},
                    "risk_level": "HIGH", "verified": True},
            "team_name": {"value": "한국생산기술연구원 융합기술연구소", "confidence": "high",
                          "match_quality": "exact", "claim_type": "qualitative",
                          "source": {"section": "Abstract", "page": 1},
                          "risk_level": "LOW", "verified": True},
        },
        "layout_variants": {"1": "A", "2": "B", "3": "B", "4": "D", "5": "A"},
    })


# ── mock 기반 단위 테스트 (LLM 호출 없음) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_s6_mock_returns_card_editor_data(agent, paper_section_map, mock_llm_response):
    """mock LLM 응답 → CardEditorData 정상 파싱."""
    from backend.core.models import S6Input, CardEditorData, PaperMetadata

    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(return_value=mock_llm_response)):
        inp = S6Input(
            job_id="test-s6-mock-001",
            section_map=paper_section_map,
            page_map={},
            paper_metadata=PaperMetadata(
                title="Fabrication of composite microbeads",
                authors=["Su Jin Ryu", "Hoik Lee"],
                year=2024,
                doi="10.1007/s10570-024-05757-4",
            ),
        )
        out = await agent.execute(inp)
    assert isinstance(out.card_data, CardEditorData)
    assert out.card_data.card1.title.value == "전기분무 기반 친환경 복합 마이크로비드 제조"


@pytest.mark.asyncio
async def test_s6_mock_verified_forced_false(agent, paper_section_map, mock_llm_response):
    """_post_process: LLM이 verified=True로 반환해도 강제 False."""
    from backend.core.models import S6Input, PaperMetadata
    from backend.agents.s6_card_json import _iter_field_values

    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(return_value=mock_llm_response)):
        inp = S6Input(job_id="test-s6-mock-002", section_map=paper_section_map,
                      page_map={}, paper_metadata=PaperMetadata(
                          title="test", authors=[], year=2024, doi=None))
        out = await agent.execute(inp)

    for fv in _iter_field_values(out.card_data):
        assert fv.verified is False, f"verified=True: {fv.value!r}"


@pytest.mark.asyncio
async def test_s6_mock_risk_levels_recalculated(agent, paper_section_map, mock_llm_response):
    """_post_process가 risk_level을 LLM 반환값 무시하고 규칙으로 재판정."""
    from backend.core.models import S6Input, PaperMetadata, RiskLevel

    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(return_value=mock_llm_response)):
        inp = S6Input(job_id="test-s6-mock-003", section_map=paper_section_map,
                      page_map={}, paper_metadata=PaperMetadata(
                          title="test", authors=[], year=2024, doi=None))
        out = await agent.execute(inp)

    cd = out.card_data
    assert cd.card1.title.risk_level == RiskLevel.HIGH       # semantic → HIGH
    assert cd.card1.mascot_bubble.risk_level == RiskLevel.HIGH  # semantic → HIGH


@pytest.mark.asyncio
async def test_s6_mock_critical_count(agent, paper_section_map, mock_llm_response):
    """CRITICAL count가 S6Output에 정확히 반영된다."""
    from backend.core.models import S6Input, PaperMetadata

    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(return_value=mock_llm_response)):
        inp = S6Input(job_id="test-s6-mock-004", section_map=paper_section_map,
                      page_map={}, paper_metadata=PaperMetadata(
                          title="test", authors=[], year=2024, doi=None))
        out = await agent.execute(inp)
    assert out.critical_count == 0  # mock 응답에 quantitative+failed 없음


@pytest.mark.asyncio
async def test_s6_mock_llm_failure_retries(agent, paper_section_map):
    """LLM이 3회 연속 실패 → ERR-S6-001 발생."""
    from backend.core.models import S6Input, PaperMetadata

    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(side_effect=RuntimeError("mock API error"))):
        inp = S6Input(job_id="test-s6-mock-005", section_map=paper_section_map,
                      page_map={}, paper_metadata=PaperMetadata(
                          title="test", authors=[], year=2024, doi=None))
        with pytest.raises(RuntimeError, match="ERR-S6-001"):
            await agent.execute(inp)


# ── 로직 단위 테스트 ──────────────────────────────────────────────────────────

def test_post_process_critical_rule(agent, mock_card_data):
    """quantitative + failed → CRITICAL."""
    from backend.core.models import RiskLevel, MatchQuality, ClaimType

    fv = mock_card_data.card3.achievement
    fv.claim_type = ClaimType.QUANTITATIVE
    fv.match_quality = MatchQuality.FAILED

    processed = agent._post_process(mock_card_data)
    assert processed.card3.achievement.risk_level == RiskLevel.CRITICAL


def test_post_process_fuzzy_becomes_high(agent, mock_card_data):
    """fuzzy → HIGH."""
    from backend.core.models import RiskLevel, MatchQuality

    mock_card_data.card2.intro.match_quality = MatchQuality.FUZZY
    processed = agent._post_process(mock_card_data)
    assert processed.card2.intro.risk_level == RiskLevel.HIGH


def test_extract_json_code_block(agent):
    result = agent._extract_json('```json\n{"meta": {}}\n```')
    assert result == '{"meta": {}}'


def test_format_section_map_truncates(agent):
    big_map = {"Section": "x" * 15000}
    result = agent._format_section_map(big_map)
    assert len(result) <= agent.SECTION_MAX_CHARS + 200


# ── 실제 API 호출 (격리된 integration 마크) ──────────────────────────────────

@pytest.mark.integration
@pytest.mark.asyncio
async def test_s6_real_api(agent, paper_section_map):
    """실제 Gemini API 호출 — `pytest -m integration`으로만 실행."""
    import os
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")

    from backend.core.models import S6Input, CardEditorData, PaperMetadata

    inp = S6Input(
        job_id="test-s6-real",
        section_map=paper_section_map,
        page_map={},
        paper_metadata=PaperMetadata(
            title="Fabrication of composite microbeads",
            authors=["Su Jin Ryu", "Hoik Lee"],
            year=2024,
            doi="10.1007/s10570-024-05757-4",
        ),
    )
    out = await agent.execute(inp)
    assert isinstance(out.card_data, CardEditorData)
    print(f"\n  card1.title: {out.card_data.card1.title.value}")
    print(f"  CRITICAL={out.critical_count} HIGH={out.high_count}")
