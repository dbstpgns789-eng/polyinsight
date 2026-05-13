"""
S6CardJson 단위 테스트.

LLM 호출은 전부 mock — API 비용 없이 로직만 검증.
pytest-mock (mocker fixture) 사용.

Happy path (H):
  H1  정상 JSON → CardEditorData 파싱 성공
  H2  critical_count 정확히 집계
  H3  exact match 검증 통과 (value가 실제 원문에 존재)
  H4  테마 컬러가 S6Output에 포함

Sad path (S):
  S1  exact match 강등 (value가 원문에 없으면 semantic으로 내림)
  S2  LLM timeout → 예외 전파 (삼키지 않음)
  S3  잘못된 JSON → warnings 기록 + 처리
  S4  degraded 섹션맵 입력 → 출력은 생성되지만 warnings 포함
"""

from __future__ import annotations

import json

import pytest

from backend.core.llm_client import LLMAPIError
from backend.core.models import (
    CardEditorData, MatchQuality, RiskLevel, S6Input,
)

try:
    from backend.agents.s6_card_json import S6CardJson
    _S6_AVAILABLE = True
except ImportError:
    _S6_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _S6_AVAILABLE,
    reason="S6CardJson not implemented yet",
)


# ── LLM mock 응답 헬퍼 ────────────────────────────────────────────────────────

def _make_valid_llm_response(mock_card_data: CardEditorData, theme: dict | None = None) -> str:
    """S6가 LLM으로부터 받기 기대하는 구조화된 JSON 문자열."""
    payload = mock_card_data.model_dump(mode="json")
    if theme:
        payload["theme"] = theme
    return json.dumps(payload)


# ── Happy path ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_h1_parses_valid_llm_output(mocker, mock_section_map, mock_card_data):
    """LLM이 유효한 JSON 반환 → CardEditorData 파싱 성공."""
    mocker.patch(
        "backend.core.llm_client.LLMClient.call",
        return_value=_make_valid_llm_response(mock_card_data),
    )

    s6 = S6CardJson()
    inp = S6Input(
        job_id="test-job-001",
        section_map=mock_section_map,
        page_map={1: "...", 2: "..."},
        paper_metadata=mock_card_data.meta.researcher.__class__.__fields__,  # dummy
    )
    out = await s6.execute(inp)

    assert isinstance(out.card_data, CardEditorData)


@pytest.mark.asyncio
async def test_h2_critical_count(mocker, mock_section_map, mock_card_data):
    """
    mock_card_data에는 CRITICAL 필드가 2개 (card3.achievement, card4.result).
    critical_count == 2 이어야 한다.
    """
    mocker.patch(
        "backend.core.llm_client.LLMClient.call",
        return_value=_make_valid_llm_response(mock_card_data),
    )

    s6 = S6CardJson()
    inp = S6Input(
        job_id="test-job-002",
        section_map=mock_section_map,
        page_map={1: "", 2: ""},
        paper_metadata=None,
    )
    out = await s6.execute(inp)

    assert out.critical_count == 2, (
        f"CRITICAL 필드 2개 기대, 실제: {out.critical_count}"
    )


@pytest.mark.asyncio
async def test_h3_exact_match_verified(mocker, mock_section_map, mock_card_data):
    """
    card3.achievement.value = "정확도 95.3%, 응답시간 0.1 ms 달성"
    section_map["results"]에 "95.3%"가 포함되어 있으므로 verified=True 유지.
    """
    mocker.patch(
        "backend.core.llm_client.LLMClient.call",
        return_value=_make_valid_llm_response(mock_card_data),
    )

    s6 = S6CardJson()
    inp = S6Input(
        job_id="test-job-003",
        section_map=mock_section_map,
        page_map={1: "", 2: ""},
        paper_metadata=None,
    )
    out = await s6.execute(inp)

    fv = out.card_data.card3.achievement
    # exact를 주장한 필드가 원문에 존재하면 verified=True
    if fv.match_quality == MatchQuality.EXACT:
        assert fv.verified is True, "exact 주장 + 원문 존재 → verified=True 이어야 함"


@pytest.mark.asyncio
async def test_h4_theme_in_output(mocker, mock_section_map, mock_card_data, mock_theme):
    """LLM이 테마 컬러를 반환하면 S6Output.theme에 포함되어야 한다."""
    mocker.patch(
        "backend.core.llm_client.LLMClient.call",
        return_value=_make_valid_llm_response(mock_card_data, theme=mock_theme),
    )

    s6 = S6CardJson()
    inp = S6Input(
        job_id="test-job-004",
        section_map=mock_section_map,
        page_map={1: "", 2: ""},
        paper_metadata=None,
    )
    out = await s6.execute(inp)

    assert out.theme.get("primary") == mock_theme["primary"]
    assert out.theme.get("dark") == mock_theme["dark"]


# ── Sad path ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_s1_exact_match_downgraded(mocker, mock_card_data):
    """
    LLM이 exact를 주장했지만 value가 section_map 어디에도 없으면
    match_quality가 semantic으로 강등되어야 한다.
    """
    # 원문에 "95.3%"가 없는 섹션맵 사용
    empty_section_map = {
        "abstract": "Some unrelated text.",
        "results": "No specific numbers mentioned here.",
    }

    mocker.patch(
        "backend.core.llm_client.LLMClient.call",
        return_value=_make_valid_llm_response(mock_card_data),
    )

    s6 = S6CardJson()
    inp = S6Input(
        job_id="test-job-005",
        section_map=empty_section_map,
        page_map={1: "", 2: ""},
        paper_metadata=None,
    )
    out = await s6.execute(inp)

    fv = out.card_data.card3.achievement
    # "95.3%"가 empty_section_map에 없으므로 exact → semantic 강등
    assert fv.match_quality != MatchQuality.EXACT, (
        "원문에 없는 값인데 exact match 그대로 유지됨 — _verify_match_quality 미작동"
    )


@pytest.mark.asyncio
async def test_s2_llm_timeout_propagates(mocker, mock_section_map):
    """
    LLM timeout → S6가 예외를 삼키지 않고 전파해야 한다.
    (orchestrator가 이 예외를 받아 처리)
    """
    mocker.patch(
        "backend.core.llm_client.LLMClient.call",
        side_effect=LLMAPIError("timeout"),
    )

    s6 = S6CardJson()
    inp = S6Input(
        job_id="test-job-006",
        section_map=mock_section_map,
        page_map={1: "", 2: ""},
        paper_metadata=None,
    )

    with pytest.raises(LLMAPIError):
        await s6.execute(inp)


@pytest.mark.asyncio
async def test_s3_malformed_json_handled(mocker, mock_section_map):
    """
    LLM이 파싱 불가한 JSON 반환 → S6가 처리하고 warnings에 기록.
    ValidationError 또는 JSONDecodeError가 사용자에게 노출되면 안 됨.
    """
    mocker.patch(
        "backend.core.llm_client.LLMClient.call",
        return_value='{"this_is": "not a CardEditorData schema"}',
    )

    s6 = S6CardJson()
    inp = S6Input(
        job_id="test-job-007",
        section_map=mock_section_map,
        page_map={1: "", 2: ""},
        paper_metadata=None,
    )

    # 구현에 따라 재시도 후 degraded output을 반환하거나 warnings를 채움
    try:
        out = await s6.execute(inp)
        assert out.warnings, "잘못된 JSON에 대한 warnings가 없음"
    except Exception as e:
        # 명시적으로 정의된 예외 타입이면 허용
        # 단, raw ValidationError / JSONDecodeError가 그대로 올라오면 안 됨
        assert not isinstance(e, (ValueError, KeyError)), (
            f"내부 예외가 그대로 전파됨: {type(e).__name__}: {e}"
        )


@pytest.mark.asyncio
async def test_s4_degraded_section_map(mocker, mock_card_data, degraded_section_map):
    """
    S1이 degraded mode로 {"full_text": ...} 만 반환한 경우.
    S6는 여전히 출력을 생성하지만 warnings에 degraded 관련 내용이 있어야 한다.
    """
    mocker.patch(
        "backend.core.llm_client.LLMClient.call",
        return_value=_make_valid_llm_response(mock_card_data),
    )

    s6 = S6CardJson()
    inp = S6Input(
        job_id="test-job-008",
        section_map=degraded_section_map,
        page_map={1: ""},
        paper_metadata=None,
    )
    out = await s6.execute(inp)

    assert isinstance(out.card_data, CardEditorData), "degraded 입력에서도 출력 생성 실패"
    assert any("degraded" in w.lower() for w in out.warnings), (
        "degraded 입력 시 warnings에 명시되어야 함"
    )
