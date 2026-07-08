# -*- coding: utf-8 -*-
"""저작 HTML 덱 → 카드별 PNG (헌법 v3.0 S7 대체 경로).

레거시 S7과 달리 React render 라우트를 거치지 않는다. 저작 HTML은 self-contained라
Playwright page.set_content()로 직접 렌더하고 [data-screen-label] 요소를 각각 스크린샷.
Windows ProactorEventLoop 격리는 s7_renderer.py 패턴을 복제.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from playwright.async_api import async_playwright

from ...core import db

logger = logging.getLogger(__name__)

# 전용 스레드풀 — 각 스레드가 독립 ProactorEventLoop (s7_renderer 패턴)
_deck_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="deck-playwright")

_CARD_W = 1080
_CARD_H = 1350  # 4:5 세로

# 저장 HTML의 자산 URL 패턴. 렌더 직전 DB 바이트→data URI로 인라인(스펙 §4.2).
_ASSET_URL_RE = re.compile(r'/api/deck/([\w-]+)/assets/([\w-]+)')


async def _inline_deck_assets(html: str, job_id: str | None) -> str:
    """set_content 전, 자산 URL을 DB 바이트→data URI로 치환.
    Playwright는 쿠키·base URL이 없어 authed 자산 URL을 못 불러온다(조용한 빈칸 렌더).
    인라인으로 self-contained HTML을 확보해 미리보기와 export PNG가 같은 픽셀로 수렴."""
    if not job_id or "/api/deck/" not in html:
        return html
    seen: dict[str, str] = {}
    for m in _ASSET_URL_RE.finditer(html):
        aid = m.group(2)
        if aid in seen:
            continue
        asset = await db.get_deck_asset(job_id, aid)
        if not asset or asset.get("bytes") is None:
            seen[aid] = ""   # 만료/부재 → 치환 안 함(§7: 플레이스홀더로 렌더 계속)
            continue
        b64 = base64.b64encode(asset["bytes"]).decode("ascii")
        seen[aid] = f'data:{asset["mime"] or "image/png"};base64,{b64}'

    def _repl(mm: "re.Match[str]") -> str:
        aid = mm.group(2)
        uri = seen.get(aid, "")
        return uri or mm.group(0)

    return _ASSET_URL_RE.sub(_repl, html)


async def _render_async(
    html: str, scale: int, timeout_s: float, job_id: str | None = None
) -> tuple[list[bytes], list[str]]:
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
            # 안전망: 이미지 decode 완료 대기(networkidle이 디코드를 보장 안 함 → 부분 캡처 방지)
            try:
                await page.evaluate(
                    "() => Promise.all(Array.from(document.images)"
                    ".map(i => (i.decode ? i.decode().catch(() => {}) : null)))"
                )
            except Exception:
                pass
            # 안전망: 카드 내용이 박스(1350)를 넘치면 비례 축소(덱엔 CardSurface 자동fit 없음).
            # 넘치는 카드만 자식을 래퍼로 묶어 scale — 정상 카드는 손대지 않음.
            try:
                await page.evaluate("""() => {
                  document.querySelectorAll('[data-screen-label]').forEach(card => {
                    if (card.scrollHeight <= card.clientHeight + 4) return;
                    const cs = getComputedStyle(card);
                    const pt = parseFloat(cs.paddingTop) || 0, pb = parseFloat(cs.paddingBottom) || 0;
                    const wrap = document.createElement('div');
                    wrap.style.boxSizing = 'border-box';
                    wrap.style.width = '100%';
                    wrap.style.transformOrigin = 'top center';
                    if (cs.display === 'flex') { wrap.style.display = 'flex'; wrap.style.flexDirection = cs.flexDirection || 'column'; }
                    while (card.firstChild) wrap.appendChild(card.firstChild);
                    card.appendChild(wrap);
                    const avail = card.clientHeight - pt - pb;
                    const need = wrap.scrollHeight;
                    if (need > avail && avail > 0) {
                      const f = Math.max(0.7, avail / need);
                      wrap.style.height = need + 'px';
                      wrap.style.transform = 'scale(' + f + ')';
                    }
                  });
                }""")
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
                    if job_id:
                        try:
                            await db.save_card_image(job_id, i + 1, png)
                        except Exception as exc:
                            warnings.append(f"deck render: card {i + 1} save error — {exc}")
                except Exception as exc:
                    warnings.append(f"deck render: card {i + 1} error — {exc}")
        except Exception as exc:
            warnings.append(f"deck render: set_content error — {exc}")
        finally:
            await ctx.close()
            await browser.close()

    return images, warnings


def _render_sync(
    html: str, scale: int, timeout_s: float, job_id: str | None = None
) -> tuple[list[bytes], list[str]]:
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_render_async(html, scale, timeout_s, job_id))
    finally:
        loop.close()


async def render_deck(
    html: str, scale: int = 2, timeout_s: float = 30.0, job_id: str | None = None
) -> tuple[list[bytes], list[str]]:
    """저작 HTML → [PNG bytes], [warnings]. 각 [data-screen-label] 카드 1장씩(×scale 레티나).
    job_id가 있으면 렌더 전 자산 URL을 data URI로 인라인(스펙 §4.2) + 캡처 즉시 DB 저장(진행 리빌)."""
    html = await _inline_deck_assets(html, job_id)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_deck_pool, _render_sync, html, scale, timeout_s, job_id)
