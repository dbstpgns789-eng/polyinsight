"""
S7Renderer 단위 테스트.

CardEditorData는 mock_card_data fixture(2장: cover + closing) 사용.
Playwright는 실제 실행 — PNG 생성까지 검증.

Happy path (H):
  H1  카드 수만큼 PNG 생성
  H2  각 PNG가 유효한 PNG magic bytes로 시작
  H3  정상 완료 시 warnings 비어있음

Sad path (S):
  S1  알 수 없는 template_type → 해당 카드 스킵, 나머지 성공
  S2  Playwright screenshot TimeoutError → 부분 성공 + warning 추가
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.core.models import CardSlot, FieldValue, S7Input, S7Output
from tests.conftest import _fv

try:
    from backend.agents.s7_renderer import S7Renderer, S7RendererAgent
    _S7_AVAILABLE = True
except ImportError:
    _S7_AVAILABLE = False

pytestmark = [
    pytest.mark.skipif(not _S7_AVAILABLE, reason="S7Renderer not implemented"),
    pytest.mark.asyncio,
]

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# ── Happy path ────────────────────────────────────────────────────────────────

async def test_h1_produces_n_pngs(mock_card_data, mock_theme):
    """정상 입력 → cards 수만큼 PNG bytes 반환."""
    inp = S7Input(job_id="test-s7-h1", card_data=mock_card_data, theme=mock_theme)
    out: S7Output = await S7Renderer().execute(inp)

    expected = len(mock_card_data.cards)
    assert len(out.images) == expected, f"PNG {expected}장 기대, 실제: {len(out.images)}장"


async def test_h2_pngs_are_valid(mock_card_data, mock_theme):
    """각 image bytes가 PNG magic bytes로 시작해야 한다."""
    inp = S7Input(job_id="test-s7-h2", card_data=mock_card_data, theme=mock_theme)
    out: S7Output = await S7Renderer().execute(inp)

    for i, img in enumerate(out.images, start=1):
        assert img[:8] == PNG_MAGIC, f"card {i}: PNG magic bytes 없음"


async def test_h3_no_warnings_on_success(mock_card_data, mock_theme):
    """정상 완료 시 warnings 리스트가 비어있어야 한다."""
    inp = S7Input(job_id="test-s7-h3", card_data=mock_card_data, theme=mock_theme)
    out: S7Output = await S7Renderer().execute(inp)

    assert out.warnings == [], f"예상치 못한 warnings: {out.warnings}"


# ── Sad path ──────────────────────────────────────────────────────────────────

async def test_s1_unknown_template_skips_card(mock_card_data, mock_theme):
    """
    LAYOUT_TEMPLATES에 없는 template_type → 해당 카드 스킵,
    나머지 카드는 정상 렌더링, warning 추가.
    """
    import copy
    import dataclasses

    # mock_card_data에 알 수 없는 template_type 카드 1장 추가
    bad_slot = CardSlot(
        card_num=99,
        template_type="__nonexistent__",
        fields={"title": _fv("테스트")},
    )
    patched = mock_card_data.model_copy(
        update={"cards": mock_card_data.cards + [bad_slot]}
    )

    inp = S7Input(job_id="test-s7-s1", card_data=patched, theme=mock_theme)
    out: S7Output = await S7Renderer().execute(inp)

    expected_ok = len(mock_card_data.cards)   # 기존 정상 카드 수
    assert len(out.images) == expected_ok, (
        f"정상 카드 {expected_ok}장 기대, 실제: {len(out.images)}장"
    )
    assert any("__nonexistent__" in w for w in out.warnings), (
        f"unknown template warning 없음. warnings: {out.warnings}"
    )


async def test_s2_playwright_timeout_partial_success(mock_card_data, mock_theme):
    """
    2번째 카드 screenshot에서 TimeoutError 발생 →
    나머지 1장 성공, warnings에 timeout 기록.
    """
    call_count = 0
    _STUB_PNG = PNG_MAGIC + b"\x00" * 100

    original_wait_for = asyncio.wait_for

    async def patched_wait_for(coro, timeout):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            coro.close()
            raise asyncio.TimeoutError("강제 타임아웃")
        return await original_wait_for(coro, timeout)

    with patch("backend.agents.s7_renderer.asyncio.wait_for", side_effect=patched_wait_for):
        inp = S7Input(job_id="test-s7-s2", card_data=mock_card_data, theme=mock_theme)
        out: S7Output = await S7Renderer().execute(inp)

    expected_ok = len(mock_card_data.cards) - 1
    assert len(out.images) == expected_ok, (
        f"timeout 1건 → {expected_ok}장 기대, 실제: {len(out.images)}장"
    )
    assert out.warnings, "TimeoutError 발생 시 warnings가 비어있으면 안 됨"
