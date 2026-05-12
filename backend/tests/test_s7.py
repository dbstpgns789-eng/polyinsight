"""S7 PNG Renderer 통합 테스트 — Playwright headless Chromium.

실행 전 조건:
  - playwright install chromium  (최초 1회)
  - backend/templates/ 에 5개 HTML 파일 존재

생성되는 PNG: 1080×1080, 5장.
"""
from __future__ import annotations

import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

import pytest


@pytest.fixture(scope="module")
def agent():
    from backend.agents.s7_renderer import S7RendererAgent
    return S7RendererAgent()


# ── 렌더링 결과 검증 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_s7_returns_5_images(agent, mock_card_data):
    """5개 카드 템플릿 모두 정상 렌더링 → images 5개."""
    from backend.core.models import S7Input, CardTheme

    inp = S7Input(
        job_id="test-s7-001",
        card_data=mock_card_data,
        theme=CardTheme(primary="#2563EB", dark="#1A4C96"),
    )
    out = await agent.execute(inp)
    assert len(out.images) == 5, \
        f"Expected 5 images, got {len(out.images)}. Warnings: {out.warnings}"


@pytest.mark.asyncio
async def test_s7_images_are_png_bytes(agent, mock_card_data):
    """각 이미지가 PNG 시그니처(\\x89PNG)로 시작해야 한다."""
    from backend.core.models import S7Input, CardTheme

    inp = S7Input(
        job_id="test-s7-002",
        card_data=mock_card_data,
        theme=CardTheme(primary="#2563EB", dark="#1A4C96"),
    )
    out = await agent.execute(inp)
    PNG_SIG = b"\x89PNG"
    for i, img in enumerate(out.images, start=1):
        assert img[:4] == PNG_SIG, f"Card {i} is not a valid PNG"


@pytest.mark.asyncio
async def test_s7_images_min_size(agent, mock_card_data):
    """각 PNG가 최소 10KB 이상이어야 한다 (빈 스크린샷 방지)."""
    from backend.core.models import S7Input, CardTheme

    inp = S7Input(
        job_id="test-s7-003",
        card_data=mock_card_data,
        theme=CardTheme(primary="#2563EB", dark="#1A4C96"),
    )
    out = await agent.execute(inp)
    for i, img in enumerate(out.images, start=1):
        assert len(img) > 10_000, f"Card {i} PNG too small: {len(img)} bytes"


@pytest.mark.asyncio
async def test_s7_custom_theme_applied(agent, mock_card_data):
    """다른 테마 색상으로도 렌더링이 완료되어야 한다."""
    from backend.core.models import S7Input, CardTheme

    inp = S7Input(
        job_id="test-s7-004",
        card_data=mock_card_data,
        theme=CardTheme(primary="#16A34A", dark="#14532D"),  # green theme
    )
    out = await agent.execute(inp)
    assert len(out.images) == 5
    assert out.warnings == [] or all("timeout" not in w.lower() for w in out.warnings)


@pytest.mark.asyncio
async def test_s7_no_warnings_on_clean_input(agent, mock_card_data):
    """정상 입력에서는 warnings가 없어야 한다."""
    from backend.core.models import S7Input, CardTheme

    inp = S7Input(
        job_id="test-s7-005",
        card_data=mock_card_data,
        theme=CardTheme(),
    )
    out = await agent.execute(inp)
    assert out.warnings == [], f"Unexpected warnings: {out.warnings}"
