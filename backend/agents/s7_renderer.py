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

# layout variant → template file
LAYOUT_TEMPLATES: dict[str, str] = {
    "A": "type_a.html",
    "B": "type_b.html",
    "C": "type_c.html",
    "D": "type_d.html",
    "E": "type_e.html",
    "G": "type_g.html",
    "K": "type_k.html",
}

# layout_variants 비어있을 때 기본값
_DEFAULT_VARIANTS: dict[str, str] = {
    "1": "A", "2": "E", "3": "B", "4": "B", "5": "K",
}


def _build_card_context(
    card_num: int,
    card_data: CardEditorData,
    theme: CardTheme,
) -> dict:
    """카드별 Jinja2 context 생성. FieldValue.value만 추출, 이름 충돌 없음."""
    ctx: dict = {
        "theme_primary": theme.primary,
        "theme_dark": theme.dark,
        "card_num": f"{card_num:02d}",
        "org": card_data.meta.org.value,
        "dept": card_data.meta.dept.value,
        "researcher": card_data.meta.researcher.value,
        "month": card_data.meta.month.value,
        "edition_number": card_data.meta.edition_number.value,
    }

    if card_num == 1:
        ctx |= {
            "pretitle": card_data.card1.pretitle.value,
            "title": card_data.card1.title.value,
            "mascot_bubble": card_data.card1.mascot_bubble.value,
        }
    elif card_num == 2:
        ctx |= {
            "intro": card_data.card2.intro.value,
            "keyword_line": card_data.card2.keyword_line.value,
            "footnote": card_data.card2.footnote.value,
            # Type B 폴백용 제네릭 필드
            "card_label": "연구 배경",
            "section_title": card_data.card2.keyword_line.value,
            "body_text": card_data.card2.intro.value,
            "sub_text": card_data.card2.footnote.value,
        }
    elif card_num == 3:
        ctx |= {
            "problem": card_data.card3.problem.value,
            "achievement": card_data.card3.achievement.value,
            "mascot_bubble": card_data.card3.mascot_bubble.value,
            "photo_caption": card_data.card3.photo_caption.value,
            # Type B 폴백용 제네릭 필드
            "card_label": "Research Highlights",
            "section_title": "핵심 문제와 성과",
            "body_text": card_data.card3.achievement.value,
            "sub_text": card_data.card3.mascot_bubble.value,
        }
    elif card_num == 4:
        ctx |= {
            "before_label": card_data.card4.before_label.value,
            "after_label": card_data.card4.after_label.value,
            "description": card_data.card4.description.value,
            "result": card_data.card4.result.value,
            "mascot_bubble": card_data.card4.mascot_bubble.value,
            # Type B 폴백용 제네릭 필드
            "card_label": "Analysis",
            "section_title": "상세 분석",
            "body_text": card_data.card4.description.value,
            "sub_text": card_data.card4.result.value,
        }
    elif card_num == 5:
        ctx |= {
            "pre_title": card_data.card5.pre_title.value,
            "main_title": card_data.card5.main_title.value,
            "cta": card_data.card5.cta.value,
            "team_name": card_data.card5.team_name.value,
        }

    return ctx


class S7RendererAgent(BaseAgent[S7Input, S7Output]):
    """S7: CardEditorData → 5장 PNG bytes (Playwright headless Chromium)."""

    def __init__(self) -> None:
        self._jinja = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
        )

    async def execute(self, input_data: S7Input) -> S7Output:
        card_data = input_data.card_data
        theme = input_data.theme
        variants = card_data.layout_variants or _DEFAULT_VARIANTS
        images: list[bytes] = []
        warnings: list[str] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            browser_ctx = await browser.new_context(
                viewport={"width": 1080, "height": 1080},
                device_scale_factor=1,
            )

            for card_num in range(1, 6):
                variant = variants.get(str(card_num), _DEFAULT_VARIANTS[str(card_num)])
                tmpl_name = LAYOUT_TEMPLATES.get(variant, "type_b.html")
                try:
                    ctx = _build_card_context(card_num, card_data, theme)
                    html = self._jinja.get_template(tmpl_name).render(**ctx)

                    page = await browser_ctx.new_page()
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
                    logger.info(
                        "S7: card %d rendered (variant=%s, %d bytes)",
                        card_num, variant, len(png),
                    )

                except asyncio.TimeoutError:
                    msg = f"S7: card {card_num} timeout ({settings.PLAYWRIGHT_TIMEOUT_MS}ms)"
                    logger.error(msg)
                    warnings.append(msg)
                except Exception as exc:
                    msg = f"S7: card {card_num} error — {exc}"
                    logger.error(msg)
                    warnings.append(msg)

            await browser_ctx.close()
            await browser.close()

        if len(images) < 5:
            warnings.append(f"S7: partial render — {len(images)}/5 cards")

        return S7Output(images=images, warnings=warnings)


s7_agent = S7RendererAgent()
