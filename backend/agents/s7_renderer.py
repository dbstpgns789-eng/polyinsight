from __future__ import annotations

import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

from playwright.async_api import async_playwright

from .base import BaseAgent
from ..core.config import settings
from ..core.models import S7Input, S7Output

logger = logging.getLogger(__name__)

# S7 전용 스레드풀 — 각 스레드가 독립 ProactorEventLoop를 가짐
_playwright_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="s7-playwright")


async def _playwright_render_via_url_async(urls: list[str], timeout_s: float) -> tuple[list[bytes], list[str]]:
    """Playwright 렌더링 (URL goto 방식). React render 라우트를 방문해서 스크린샷.

    page.goto(Next.js URL) + [data-render-ready] 대기.
    """
    images: list[bytes] = []
    warnings: list[str] = []
    timeout_ms = timeout_s * 1000

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        browser_ctx = await browser.new_context(
            viewport={"width": 1080, "height": 1080},
            device_scale_factor=1,
        )

        for i, url in enumerate(urls, start=1):
            try:
                page = await browser_ctx.new_page()
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                # 데이터 + 폰트 로딩 완료 신호 대기 (폰트 race 방지).
                # state="attached": render 페이지 루트가 position:fixed라 body가 zero-area
                # → 기본값 state="visible"이면 hidden 판정되어 timeout. 신호는 존재 여부만 확인.
                await page.wait_for_selector("[data-render-ready]", state="attached", timeout=timeout_ms)
                png = await asyncio.wait_for(
                    page.screenshot(
                        type="png",
                        clip={"x": 0, "y": 0, "width": 1080, "height": 1080},
                        full_page=False,
                    ),
                    timeout=timeout_s,
                )
                images.append(png)
                await page.close()
                logger.info("S7: card %d rendered via URL (%d bytes)", i, len(png))
            except asyncio.TimeoutError:
                msg = f"S7: card {i} timeout ({timeout_ms:.0f}ms) — {url}"
                logger.error(msg)
                warnings.append(msg)
            except Exception as exc:
                msg = f"S7: card {i} error — {exc} ({url})"
                logger.error(msg)
                warnings.append(msg)

        await browser_ctx.close()
        await browser.close()

    return images, warnings


def _playwright_render_via_url_sync(urls: list[str], timeout_s: float) -> tuple[list[bytes], list[str]]:
    """ProactorEventLoop를 직접 생성해서 URL 기반 Playwright 렌더 실행."""
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_playwright_render_via_url_async(urls, timeout_s))
    finally:
        loop.close()


class S7RendererAgent(BaseAgent[S7Input, S7Output]):
    """S7: CardEditorData → N장 PNG bytes (Playwright headless Chromium, React render 라우트)."""

    async def execute(self, input_data: S7Input) -> S7Output:
        """CardEditorData → N장 PNG. React render 라우트(Next.js)를 goto해서 스크린샷.

        card_data는 호출 전에 DB에 저장되어 있어야 한다 (render 라우트가 DB에서 읽음).
        - orchestrator: S7 직전에 저장
        - export 엔드포인트: 이미 DB에서 읽어서 호출
        """
        job_id = input_data.job_id
        card_data = input_data.card_data
        warnings: list[str] = []

        urls = [
            f"{settings.WEB_BASE_URL}/render/{job_id}/{slot.card_num}"
            for slot in card_data.cards
        ]
        if not urls:
            return S7Output(images=[], warnings=warnings + ["S7: no renderable cards"])

        # Playwright를 전용 스레드(ProactorEventLoop)에서 실행
        timeout_s = settings.PLAYWRIGHT_TIMEOUT_MS / 1000
        loop = asyncio.get_event_loop()
        images, render_warnings = await loop.run_in_executor(
            _playwright_pool,
            _playwright_render_via_url_sync,
            urls,
            timeout_s,
        )
        warnings.extend(render_warnings)

        total = len(card_data.cards)
        if len(images) < total:
            warnings.append(f"S7: partial render — {len(images)}/{total} cards")

        return S7Output(images=images, warnings=warnings)


s7_agent = S7RendererAgent()
S7Renderer = S7RendererAgent
