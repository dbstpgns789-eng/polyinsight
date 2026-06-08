"""세트 전문화 v1 시각 게이트 — demo 8뼈대를 1080×1080으로 일괄 캡처.

각 카드를 /render/demo/{n}으로 goto → data-render-ready(attached) 대기 → clip 스크린샷.
출력: backend/scripts/gate/card_{n}.png (gitignore/삭제 대상).

실행: python -m backend.scripts.skin_gate
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

from playwright.async_api import async_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

BASE = "http://localhost:3000"
OUT_DIR = "backend/scripts/gate"
# 8뼈대 demo 카드(서사 순서): cover(1) statement(2) feature(3) process(4)
# bigstat(5) reasons(6) grid(7) closing(8)
CARDS = [1, 2, 3, 4, 5, 6, 7, 8]


async def run() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1080, "height": 1080}, device_scale_factor=1)
        page = await ctx.new_page()
        page.on("pageerror", lambda e: print(f"  [pageerror] {e}"))
        page.on("console", lambda m: print(f"  [console.{m.type}] {m.text}") if m.type == "error" else None)

        for n in CARDS:
            url = f"{BASE}/render/demo/{n}"
            t0 = time.time()
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_selector("[data-render-ready]", state="attached", timeout=10000)
                out = f"{OUT_DIR}/card_{n}.png"
                await page.screenshot(path=out, clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
                print(f"  card {n}: OK ({time.time()-t0:.1f}s) -> {out}")
            except Exception as exc:
                print(f"  card {n}: FAILED ({time.time()-t0:.1f}s) — {exc}")

        await ctx.close()
        await browser.close()


def main() -> None:
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
