from __future__ import annotations

import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

from .base import BaseAgent
from ..core.config import settings
from ..core.models import CardEditorData, CardSlot, CardTheme, S7Input, S7Output

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

LAYOUT_TEMPLATES: dict[str, str] = {
    "cover":      "cover.html",
    "hook":       "hook.html",
    "problem":    "problem.html",
    "circle3":    "circle3.html",
    "compare2":   "compare2.html",
    "grid4":      "grid4.html",
    "definition": "definition.html",
    "flow":       "flow.html",
    "data":       "data.html",
    "showcase":   "showcase.html",
    "closing":    "closing.html",
    "brand":      "brand.html",
}

IMAGE_SLOT_TYPES: dict[str, str] = {
    "cover":      "bg",
    "hook":       "bg",
    "problem":    "bg",
    "circle3":    "bg",
    "compare2":   "bg",
    "grid4":      "bg",
    "flow":       "bg",
    "showcase":   "inset_top",
    "definition": "inset_right",
    "closing":    "inner",
    "data":       "none",
    "brand":      "none",
}

# S7 전용 스레드풀 — 각 스레드가 독립 ProactorEventLoop를 가짐
_playwright_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="s7-playwright")


def get_image_slot_type(template_type: str) -> str:
    return IMAGE_SLOT_TYPES.get(template_type, "none")


def _build_card_context(
    slot: CardSlot,
    card_data: CardEditorData,
    theme: CardTheme,
) -> dict:
    ctx: dict = {
        "theme_primary": theme.primary,
        "theme_dark": theme.dark,
        "card_num": f"{slot.card_num:02d}",
        "org": card_data.meta.org.value,
        "dept": card_data.meta.dept.value,
        "researcher": card_data.meta.researcher.value,
        "month": card_data.meta.month.value,
        "edition_number": card_data.meta.edition_number.value,
        "image_url": slot.image_url or "",
        "bg_image": slot.image_url or "",
        "slot_mode": IMAGE_SLOT_TYPES.get(slot.template_type, "none"),
    }
    for key, fv in slot.fields.items():
        ctx[key] = fv.value
    return ctx


async def _playwright_render_async(html_pages: list[str], timeout_s: float) -> tuple[list[bytes], list[str]]:
    """Playwright 렌더링 (async). ProactorEventLoop 전용 스레드에서 호출됨."""
    images: list[bytes] = []
    warnings: list[str] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        browser_ctx = await browser.new_context(
            viewport={"width": 1080, "height": 1080},
            device_scale_factor=1,
        )

        for i, html in enumerate(html_pages, start=1):
            try:
                page = await browser_ctx.new_page()
                await page.set_content(html, wait_until="networkidle")
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
                logger.info("S7: card %d rendered (%d bytes)", i, len(png))
            except asyncio.TimeoutError:
                msg = f"S7: card {i} timeout ({timeout_s*1000:.0f}ms)"
                logger.error(msg)
                warnings.append(msg)
            except Exception as exc:
                msg = f"S7: card {i} error — {exc}"
                logger.error(msg)
                warnings.append(msg)

        await browser_ctx.close()
        await browser.close()

    return images, warnings


def _playwright_render_sync(html_pages: list[str], timeout_s: float) -> tuple[list[bytes], list[str]]:
    """ProactorEventLoop를 직접 생성해서 Playwright를 실행 (Windows SelectorEventLoop 우회)."""
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_playwright_render_async(html_pages, timeout_s))
    finally:
        loop.close()


async def _playwright_render_via_url_async(urls: list[str], timeout_s: float) -> tuple[list[bytes], list[str]]:
    """Playwright 렌더링 (URL goto 방식). React render 라우트를 방문해서 스크린샷.

    set_content(Jinja HTML) 대신 page.goto(Next.js URL) + [data-render-ready] 대기.
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
    """S7: CardEditorData → N장 PNG bytes (Playwright headless Chromium)."""

    def __init__(self) -> None:
        self._jinja = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
        )

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

    def render_slot_html(self, slot: CardSlot, card_data: CardEditorData, theme: CardTheme | None = None) -> str:
        """단일 CardSlot → Jinja2 렌더링 HTML 반환 (preview용, Playwright 없이)."""
        theme = theme or CardTheme()
        tmpl_name = LAYOUT_TEMPLATES.get(slot.template_type)
        if tmpl_name is None:
            return f"<div style='padding:24px;color:#64748b'>Unknown template: {slot.template_type}</div>"
        ctx = _build_card_context(slot, card_data, theme)
        return self._jinja.get_template(tmpl_name).render(**ctx)


s7_agent = S7RendererAgent()
S7Renderer = S7RendererAgent
