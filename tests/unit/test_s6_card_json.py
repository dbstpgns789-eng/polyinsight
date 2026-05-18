"""S6CardJson 단위 테스트 (v2 — storyboard-first, CardSlot 기반)

LLM 호출은 전부 mock — API 비용 없이 로직만 검증.

Happy path (H):
  H1  유효한 JSON + storyboard → CardEditorData 파싱 성공, storyboard 포함
  H2  CRITICAL 카운트 정확히 집계 (quantitative + failed)
  H3  post_process: verified 항상 False (LLM이 True로 줘도 강제 초기화)
  H4  post_process: risk_level 규칙 강제 적용

Sad path (S):
  S1  LLM 3회 연속 실패 → RuntimeError("ERR-S6-001") 전파
  S2  malformed JSON 3회 → RuntimeError 전파
  S3  DEV_MOCK_LLM=True → LLM 호출 없이 mock 데이터 반환
  S4  degraded section_map (full_text만) → 출력 생성 성공
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.s6_card_json import S6CardJsonAgent
from backend.core.llm_client import LLMAPIError
from backend.core.models import (
    CardEditorData, CardMeta, CardSlot, CardStorybeat,
    ClaimType, FieldSource, FieldValue,
    MatchQuality, PaperMetadata, RiskLevel, S6Input, Storyboard,
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _fv(
    value: str,
    *,
    section: str = "results",
    page: int = 2,
    risk: str = "LOW",
    quality: str = "exact",
    claim: str = "qualitative",
    confidence: str = "high",
) -> FieldValue:
    return FieldValue(
        value=value,
        confidence=confidence,          # type: ignore[arg-type]
        match_quality=MatchQuality(quality),
        claim_type=ClaimType(claim),
        source=FieldSource(section=section, page=page),
        risk_level=RiskLevel(risk),
    )


def _make_s6_input(section_map: dict[str, str]) -> S6Input:
    return S6Input(
        job_id="test-job",
        section_map=section_map,
        page_map={1: "page1 text", 2: "page2 text"},
        paper_metadata=PaperMetadata(
            title="CNT Gas Sensor Study",
            authors=["Kim Minjun"],
            year=2024,
            doi="10.0000/test",
        ),
        card_count=3,
    )


def _make_llm_json(card_data: CardEditorData) -> str:
    """S6가 LLM으로부터 받는 형태의 JSON 문자열 생성."""
    payload = card_data.model_dump(mode="json")
    # storyboard가 없으면 자동 생성 (cards 기반)
    if payload.get("storyboard") is None:
        payload["storyboard"] = {
            "story_arc": "CNT 가스 센서 연구의 배경·방법·성과를 소개하는 3장 카드뉴스",
            "beats": [
                {
                    "card_num": slot["card_num"],
                    "template_type": slot["template_type"],
                    "narrative_role": "테스트 역할",
                    "key_message": "테스트 핵심 메시지",
                }
                for slot in payload["cards"]
            ],
        }
    return json.dumps(payload)


# ── 공통 fixture ──────────────────────────────────────────────────────────────

@pytest.fixture
def agent() -> S6CardJsonAgent:
    return S6CardJsonAgent()


@pytest.fixture
def section_map() -> dict[str, str]:
    return {
        "abstract": (
            "We developed a carbon nanotube-based gas sensor achieving 95.3% detection "
            "accuracy with a response time of 0.1 ms."
        ),
        "results": (
            "Accuracy 95.3%, response time 0.1 ms. 40% improvement over baseline."
        ),
        "conclusion": "High-performance sensor with practical applicability confirmed.",
    }


@pytest.fixture
def card_data_3cards() -> CardEditorData:
    """3장짜리 CardEditorData (cover + showcase + closing). CRITICAL 1개 포함."""
    meta = CardMeta(
        org=_fv("한국생산기술연구원", section="abstract", page=1),
        dept=_fv("나노소재연구부", section="abstract", page=1),
        researcher=_fv("김민준", section="abstract", page=1),
        month=_fv("2024-03", section="abstract", page=1, quality="normalized"),
        edition_number=_fv("2024-01", section="abstract", page=1, quality="normalized"),
    )
    storyboard = Storyboard(
        story_arc="CNT 가스 센서의 문제, 성과, 마무리 3장 구성",
        beats=[
            CardStorybeat(card_num=1, template_type="cover",
                          narrative_role="주제 소개", key_message="CNT 가스 센서 개발"),
            CardStorybeat(card_num=2, template_type="showcase",
                          narrative_role="핵심 성과 강조", key_message="95.3% 정확도 달성"),
            CardStorybeat(card_num=3, template_type="closing",
                          narrative_role="마무리", key_message="실용화 가능성 확인"),
        ],
    )
    cards = [
        CardSlot(
            card_num=1,
            template_type="cover",
            fields={
                "title": _fv("CNT 기반 고감도 가스 센서", section="abstract", page=1),
                # quantitative + failed → post_process가 CRITICAL로 판정
                "subtitle": _fv("95.3% 정확도·0.1 ms 응답속도",
                                section="results", page=2,
                                risk="CRITICAL", quality="failed", claim="quantitative"),
            },
        ),
        CardSlot(
            card_num=2,
            template_type="showcase",
            fields={
                "title": _fv("연구 핵심 성과", section="results", page=2),
                "body": _fv("기존 대비 40% 향상", section="results", page=2,
                            claim="quantitative", quality="exact"),
                # quantitative + failed → CRITICAL
                "icon1": _fv("정확도:95.3%", section="results", page=2,
                             risk="CRITICAL", quality="failed", claim="quantitative"),
            },
        ),
        CardSlot(
            card_num=3,
            template_type="closing",
            fields={
                "title_white": _fv("더 안전한 미래를", section="conclusion", page=2),
                "title_accent": _fv("CNT로", section="conclusion", page=2),
                "body": _fv("실용화 가능성 확인", section="conclusion", page=2),
            },
        ),
    ]
    return CardEditorData(storyboard=storyboard, meta=meta, cards=cards)


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_h1_parses_valid_llm_output(agent, section_map, card_data_3cards):
    """유효한 JSON + storyboard → CardEditorData 파싱 성공, storyboard 포함."""
    mock_response = _make_llm_json(card_data_3cards)

    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(return_value=mock_response)):
        out = await agent.execute(_make_s6_input(section_map))

    assert isinstance(out.card_data, CardEditorData)
    assert len(out.card_data.cards) == 3
    assert out.card_data.storyboard is not None
    assert out.card_data.storyboard.story_arc != ""
    assert len(out.card_data.storyboard.beats) == 3


@pytest.mark.asyncio
async def test_h2_critical_count(agent, section_map, card_data_3cards, monkeypatch):
    """CRITICAL 필드(quantitative + exact) 카운트 정확히 집계."""
    from backend.core import config as cfg
    monkeypatch.setattr(cfg.settings, "DEV_MOCK_LLM", False)
    mock_response = _make_llm_json(card_data_3cards)

    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(return_value=mock_response)):
        out = await agent.execute(_make_s6_input(section_map))

    # card_data_3cards에 CRITICAL 필드: cover.subtitle, showcase.icon1 → 2개
    assert out.critical_count == 2, (
        f"CRITICAL 2개 기대, 실제: {out.critical_count}"
    )


@pytest.mark.asyncio
async def test_h3_verified_always_false(agent, section_map, card_data_3cards, monkeypatch):
    """LLM이 verified=True를 반환해도 post_process가 False로 강제."""
    from backend.core import config as cfg
    monkeypatch.setattr(cfg.settings, "DEV_MOCK_LLM", False)
    payload = json.loads(_make_llm_json(card_data_3cards))
    # 모든 FieldValue에 verified=True 주입
    for card in payload["cards"]:
        for fv in card["fields"].values():
            fv["verified"] = True
    for fv in payload["meta"].values():
        if isinstance(fv, dict):
            fv["verified"] = True

    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(return_value=json.dumps(payload))):
        out = await agent.execute(_make_s6_input(section_map))

    for slot in out.card_data.cards:
        for fv in slot.fields.values():
            assert fv.verified is False, (
                f"card{slot.card_num}.{fv}: verified=True가 그대로 유지됨"
            )


@pytest.mark.asyncio
async def test_h4_risk_level_rules_enforced(agent, section_map, card_data_3cards, monkeypatch):
    """post_process: quantitative+failed → CRITICAL, fuzzy → HIGH 규칙 강제."""
    from backend.core import config as cfg
    monkeypatch.setattr(cfg.settings, "DEV_MOCK_LLM", False)
    payload = json.loads(_make_llm_json(card_data_3cards))
    # cover.title을 quantitative+failed로 조작 (risk_level은 LOW로 잘못 설정)
    payload["cards"][0]["fields"]["title"]["claim_type"] = "quantitative"
    payload["cards"][0]["fields"]["title"]["match_quality"] = "failed"
    payload["cards"][0]["fields"]["title"]["risk_level"] = "LOW"  # 잘못된 값

    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(return_value=json.dumps(payload))):
        out = await agent.execute(_make_s6_input(section_map))

    cover_title = out.card_data.cards[0].fields["title"]
    assert cover_title.risk_level == RiskLevel.CRITICAL, (
        "quantitative + failed → CRITICAL 규칙이 적용되지 않음"
    )


# ── Sad path ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_s1_llm_three_failures_raises(agent, section_map, monkeypatch):
    """LLM 3회 연속 실패 → RuntimeError('ERR-S6-001') 전파."""
    from backend.core import config as cfg
    monkeypatch.setattr(cfg.settings, "DEV_MOCK_LLM", False)
    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(side_effect=LLMAPIError("timeout"))):
        with pytest.raises(RuntimeError, match="ERR-S6-001"):
            await agent.execute(_make_s6_input(section_map))


@pytest.mark.asyncio
async def test_s2_malformed_json_raises(agent, section_map, monkeypatch):
    """LLM이 파싱 불가 JSON 3회 반환 → RuntimeError 전파."""
    from backend.core import config as cfg
    monkeypatch.setattr(cfg.settings, "DEV_MOCK_LLM", False)
    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(return_value='{"this_is": "not a valid schema"}')):
        with pytest.raises(RuntimeError, match="ERR-S6-001"):
            await agent.execute(_make_s6_input(section_map))


@pytest.mark.asyncio
async def test_s3_dev_mock_llm_skips_call(section_map, monkeypatch):
    """DEV_MOCK_LLM=True → LLM 호출 없이 mock 데이터 반환."""
    from backend.core import config as cfg
    monkeypatch.setattr(cfg.settings, "DEV_MOCK_LLM", True)

    agent = S6CardJsonAgent()
    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(side_effect=AssertionError("LLM이 호출됨"))) as mock_call:
        out = await agent.execute(_make_s6_input(section_map))
        mock_call.assert_not_called()

    assert isinstance(out.card_data, CardEditorData)
    assert len(out.card_data.cards) > 0
    # mock 데이터도 storyboard 포함 확인
    assert out.card_data.storyboard is not None


@pytest.mark.asyncio
async def test_s4_degraded_section_map(agent, card_data_3cards):
    """degraded section_map (full_text만) → 출력 생성 성공."""
    degraded_map = {
        "full_text": (
            "CNT gas sensor with 95.3% accuracy and 0.1 ms response time. "
            "CVD synthesis. Practical applicability confirmed."
        )
    }
    mock_response = _make_llm_json(card_data_3cards)

    with patch("backend.agents.s6_card_json.llm_client.call",
               new=AsyncMock(return_value=mock_response)):
        out = await agent.execute(_make_s6_input(degraded_map))

    assert isinstance(out.card_data, CardEditorData)
    assert len(out.card_data.cards) > 0
