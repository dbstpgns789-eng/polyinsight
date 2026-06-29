# -*- coding: utf-8 -*-
"""저작 HTML 덱 → 카드별 PNG (헌법 v3.0 S7 대체 경로).

레거시 S7과 달리 React render 라우트를 거치지 않는다. 저작 HTML은 self-contained라
Playwright page.set_content()로 직접 렌더하고 [data-screen-label] 요소를 각각 스크린샷.
Windows ProactorEventLoop 격리는 s7_renderer.py 패턴을 복제.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# 전용 스레드풀 — 각 스레드가 독립 ProactorEventLoop (s7_renderer 패턴)
_deck_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="deck-playwright")

_CARD_W = 1080
_CARD_H = 1350  # 4:5 세로


async def _render_async(html: str, scale: int, timeout_s: float) -> tuple[list[bytes], list[str]]:
    images: list[bytes] = []
    warnings: list[str] = []
    timeout_ms = timeout_s * 1000

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": _CARD_W, "height": _CARD_H},
            device_scale_factor=scale,
        )
        page = await ctx.new_page()
        try:
            await page.set_content(html, wait_until="networkidle", timeout=timeout_ms)
            # 웹폰트 race 방지 — 폰트 로딩 완료 대기
            try:
                await page.evaluate("document.fonts && document.fonts.ready")
            except Exception:
                pass
            loc = page.locator("[data-screen-label]")
            count = await loc.count()
            if count == 0:
                warnings.append("deck render: no [data-screen-label] cards found")
            for i in range(count):
                try:
                    png = await asyncio.wait_for(
                        loc.nth(i).screenshot(type="png"), timeout=timeout_s
                    )
                    images.append(png)
                    logger.info("deck render: card %d (%d bytes)", i + 1, len(png))
                except Exception as exc:
                    warnings.append(f"deck render: card {i + 1} error — {exc}")
        except Exception as exc:
            warnings.append(f"deck render: set_content error — {exc}")
        finally:
            await ctx.close()
            await browser.close()

    return images, warnings


def _render_sync(html: str, scale: int, timeout_s: float) -> tuple[list[bytes], list[str]]:
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_render_async(html, scale, timeout_s))
    finally:
        loop.close()


async def render_deck(html: str, scale: int = 2, timeout_s: float = 30.0) -> tuple[list[bytes], list[str]]:
    """저작 HTML → [PNG bytes], [warnings]. 각 [data-screen-label] 카드 1장씩(×scale 레티나)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_deck_pool, _render_sync, html, scale, timeout_s)
