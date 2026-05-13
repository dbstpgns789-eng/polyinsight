"""
S7Renderer 단위 테스트.

실제 Playwright 실행 (설치됨) — Playwright 자체는 mock하지 않는다.
CardEditorData는 mock_card_data fixture로 대체.

Happy path (H):
  H1  5장 PNG 생성
  H2  각 PNG가 유효한 PNG 바이트 (magic bytes 확인)
  H3  정상 완료 시 warnings 비어있음

Sad path (S):
  S1  템플릿 파일 누락 → 해당 카드 스킵, 나머지 성공
  S2  Playwright screenshot 실패 시 부분 성공 (mock 사용)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.models import S7Input, S7Output

try:
    from backend.agents.s7_renderer import S7Renderer
    _S7_AVAILABLE = True
except ImportError:
    _S7_AVAILABLE = False

pytestmark = [
    pytest.mark.skipif(not _S7_AVAILABLE, reason="S7Renderer not implemented yet"),
    pytest.mark.asyncio,
]

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# ── Happy path ───────────────────────────────────────────────────────────────

async def test_h1_produces_5_pngs(mock_card_data, mock_theme):
    """정상 입력 → 5장의 PNG bytes 반환."""
    inp = S7Input(job_id="test-s7-001", card_data=mock_card_data, theme=mock_theme)
    out: S7Output = await S7Renderer().execute(inp)

    assert len(out.images) == 5, f"PNG 5장 기대, 실제: {len(out.images)}장"


async def test_h2_pngs_are_valid(mock_card_data, mock_theme):
    """각 image bytes가 PNG magic bytes로 시작해야 한다."""
    inp = S7Input(job_id="test-s7-002", card_data=mock_card_data, theme=mock_theme)
    out: S7Output = await S7Renderer().execute(inp)

    for i, img in enumerate(out.images, start=1):
        assert img[:8] == PNG_MAGIC, f"card {i}: PNG magic bytes 없음"


async def test_h3_no_warnings_on_success(mock_card_data, mock_theme):
    """정상 완료 시 warnings 리스트가 비어있어야 한다."""
    inp = S7Input(job_id="test-s7-003", card_data=mock_card_data, theme=mock_theme)
    out: S7Output = await S7Renderer().execute(inp)

    assert out.warnings == [], f"예상치 못한 warnings: {out.warnings}"


# ── Sad path ─────────────────────────────────────────────────────────────────

async def test_s1_missing_template_skips_card(mock_card_data, mock_theme, tmp_path, monkeypatch):
    """
    card_grid.html (카드 3번 템플릿)이 없으면
    해당 카드는 건너뛰고 나머지 4장이 성공해야 한다.
    """
    from backend.core import config as cfg_module

    # tmp_path에 card_grid.html 제외 4개 템플릿만 만들어 설정
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    for name in ["card_cover.html", "card_hook.html", "card_text.html", "card_closing.html"]:
        (templates_dir / name).write_text(
            "<html><body><canvas width='1080' height='1080'></canvas></body></html>"
        )
    # card_grid.html 은 의도적으로 생성 안 함

    monkeypatch.setattr(cfg_module.settings, "TEMPLATES_DIR", templates_dir)

    inp = S7Input(job_id="test-s7-004", card_data=mock_card_data, theme=mock_theme)
    out: S7Output = await S7Renderer().execute(inp)

    assert len(out.images) == 4, f"카드 1개 누락 기대, 실제: {len(out.images)}장"
    assert any("card 3" in w or "card3" in w for w in out.warnings), (
        f"card 3 누락 관련 warning 없음. warnings: {out.warnings}"
    )


async def test_s2_playwright_timeout_partial_success(mock_card_data, mock_theme):
    """
    Playwright screenshot이 카드 3번에서 TimeoutError를 raise할 때
    나머지 4장은 성공하고 warning이 추가되어야 한다.
    """
    call_count = 0
    original_screenshot = None  # 실제 메서드를 나중에 복원

    async def mock_screenshot(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 3:  # 3번째 카드에서 타임아웃
            raise asyncio.TimeoutError("Playwright 강제 타임아웃")
        return PNG_MAGIC + b"\x00" * 100  # 최소 PNG stub

    with patch("playwright.async_api.Page.screenshot", new=mock_screenshot):
        inp = S7Input(job_id="test-s7-005", card_data=mock_card_data, theme=mock_theme)
        out: S7Output = await S7Renderer().execute(inp)

    assert len(out.images) == 4, f"카드 1개 실패 기대, 실제: {len(out.images)}장"
    assert out.warnings, "타임아웃 발생 시 warnings가 있어야 함"
