"""S7 render 라우트 진단 도구 — Playwright가 어디서 실패하는지 증거 수집.

S7(React goto 렌더)이 빈 PNG를 내거나 타임아웃할 때, 각 단계
(goto / networkidle / data-render-ready / body 상태 / fonts.status)를 로깅하고
스크린샷(backend/scripts/debug_shot.png, gitignore)을 저장한다.
demo로 격리하면 DB/fetch 변수가 제거된다.

주의: 이 스크립트의 wait_for_selector는 진단용으로 기본값(state="visible")을 쓰므로
render 루트(position:fixed)에서는 "NOT FOUND"가 뜰 수 있다. 이는 정상이며,
prod(s7_renderer.py)는 state="attached"를 사용한다. body.innerText/스크린샷으로 실제
렌더 여부를 판단할 것.

실행: python -m backend.scripts.s7_render_check [demo|<jobId>] [card_num]
"""
from __future__ import annotations

import asyncio
import sys
import time

from playwright.async_api import async_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

BASE = "http://localhost:3000"


async def debug_one(url: str, timeout_ms: float) -> None:
    print(f"\n=== {url} ===")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1080, "height": 1080}, device_scale_factor=1)
        page = await ctx.new_page()

        # 콘솔/네트워크 실패 캡처
        page.on("console", lambda m: print(f"  [console.{m.type}] {m.text}"))
        page.on("pageerror", lambda e: print(f"  [pageerror] {e}"))
        page.on("requestfailed", lambda r: print(f"  [reqfailed] {r.url} :: {r.failure}"))

        t0 = time.time()
        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            print(f"  goto+networkidle OK ({time.time()-t0:.1f}s)")
        except Exception as exc:
            print(f"  goto FAILED ({time.time()-t0:.1f}s): {exc}")

        # data-render-ready 존재 여부
        try:
            await page.wait_for_selector("[data-render-ready]", timeout=5000)
            print("  data-render-ready: FOUND")
        except Exception as exc:
            print(f"  data-render-ready: NOT FOUND — {exc}")

        # body 상태 덤프
        body_text = await page.evaluate("() => document.body.innerText.slice(0, 200)")
        has_attr = await page.evaluate("() => document.body.hasAttribute('data-render-ready')")
        fonts_status = await page.evaluate("() => document.fonts.status")
        print(f"  body.innerText[:200]: {body_text!r}")
        print(f"  body has data-render-ready attr: {has_attr}")
        print(f"  document.fonts.status: {fonts_status}")

        await page.screenshot(path="backend/scripts/debug_shot.png", clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
        print("  screenshot saved: backend/scripts/debug_shot.png")

        await ctx.close()
        await browser.close()


def main() -> None:
    job = sys.argv[1] if len(sys.argv) > 1 else "demo"
    card = sys.argv[2] if len(sys.argv) > 2 else "1"
    url = f"{BASE}/render/{job}/{card}"

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(debug_one(url, 15000))
    finally:
        loop.close()


if __name__ == "__main__":
    main()
