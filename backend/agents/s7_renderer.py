from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

from .base import BaseAgent
from ..core.config import settings
from ..core.models import CardEditorData, CardTheme, S7Input, S7Output

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# 카드 번호 → 템플릿 파일명
CARD_TEMPLATES = {
    1: "cover.html",
    2: "hook.html",
    3: "grid.html",
    4: "text.html",
    5: "closing.html",
}


def _flatten(card_data: CardEditorData) -> dict:
    """CardEditorData의 FieldValue.value만 추출한 평탄 dict."""
    flat: dict = {}

    def _extract(obj, prefix=""):
        for k, v in vars(obj).items():
            from ..core.models import FieldValue
            if isinstance(v, FieldValue):
                flat[f"{prefix}{k}" if not prefix else k] = v.value
            elif hasattr(v, "__dict__"):
                _extract(v, prefix)

    for group_name in ["meta", "card1", "card2", "card3", "card4", "card5"]:
        group = getattr(card_data, group_name)
        _extract(group)

    flat["layout_variants"] = card_data.layout_variants
    return flat


def _card_context(card_num: int, flat: dict, theme: CardTheme) -> dict:
    """각 카드 템플릿에 필요한 context 구성."""
    ctx = dict(flat)
    ctx["theme_primary"] = theme.primary
    ctx["theme_dark"] = theme.dark
    ctx["card_num"] = card_num
    return ctx


class S7RendererAgent(BaseAgent[S7Input, S7Output]):
    """S7: CardEditorData → PNG bytes (Playwright headless Chromium)."""

    def __init__(self) -> None:
        self._jinja = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
        )

    async def execute(self, input_data: S7Input) -> S7Output:
        flat = _flatten(input_data.card_data)
        theme = input_data.theme
        images: list[bytes] = []
        warnings: list[str] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1080, "height": 1080},
                device_scale_factor=1,
            )

            for card_num, tmpl_name in CARD_TEMPLATES.items():
                try:
                    ctx = _card_context(card_num, flat, theme)
                    html = self._jinja.get_template(tmpl_name).render(**ctx)

                    page = await context.new_page()
                    await page.set_content(html, wait_until="networkidle")

                    png = await asyncio.wait_for(
                        page.screenshot(
                            type="png",
                            clip={"x": 0, "y": 0, "width": 1080, "height": 1080},
                            full_page=False,
                        ),
                        timeout=settings.PLAYWRIGHT_TIMEOUT_MS / 1000,
                    )
                    images.append(png)
                    await page.close()
                    logger.info("S7: card %d rendered (%d bytes)", card_num, len(png))

                except asyncio.TimeoutError:
                    msg = f"S7: card {card_num} timeout ({settings.PLAYWRIGHT_TIMEOUT_MS}ms)"
                    logger.error(msg)
                    warnings.append(msg)
                except Exception as exc:
                    msg = f"S7: card {card_num} error — {exc}"
                    logger.error(msg)
                    warnings.append(msg)

            await context.close()
            await browser.close()

        if len(images) < len(CARD_TEMPLATES):
            warnings.append(
                f"S7: partial render — {len(images)}/{len(CARD_TEMPLATES)} cards"
            )

        return S7Output(images=images, warnings=warnings)


s7_agent = S7RendererAgent()
