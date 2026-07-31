# -*- coding: utf-8 -*-
"""프리즈가 겹침 순서(z-order)를 바꾸는지 — 2026-07-30.

제보: 편집 모드에서 요소가 다른 요소 뒤로 가려진다.

가설: CSS 페인팅 순서상 positioned(absolute/relative) 요소는 static 요소보다 **항상 위**에
  그려진다(z-index가 없어도). 그런데 freezeCard는 카드 안 모든 흐름 요소를 absolute로 승격한다.
  그러면 전부 positioned가 되어 그 우선권이 사라지고 **문서 순서**가 지배한다.
    · 승격 전: A(absolute, 문서 먼저)  >  B(static, 문서 나중)   ← A가 위
    · 승격 후: A(absolute), B(absolute) → 문서 순서 → B가 위     ← ★역전
  즉 원래 앞에 있던 요소가 뒤로 숨는다. 뷰어 PNG는 freeze를 안 거치므로 정상이고,
  편집기에서만 어긋난다.

실행: .venv/Scripts/python.exe web/harness/freeze_zorder.py   (레포 루트에서)
종료코드 0=PASS, 1=FAIL.
"""
import asyncio
import pathlib
import sys

from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
AGENT_TS = ROOT / "web" / "src" / "components" / "deck" / "editorAgent.ts"


def extract_agent_body() -> str:
    src = AGENT_TS.read_text(encoding="utf-8")
    marker = "const AGENT_BODY = `"
    start = src.index(marker) + len(marker)
    end = src.index("`;", start)
    body = src[start:end]
    return body.replace("\\\\", "\\").replace("\\`", "`").replace("\\${", "${")


# 앞(absolute, 문서 먼저) 위에 뒤(static, 문서 나중)가 겹치도록 배치.
# 승격 전에는 CSS 규칙상 앞이 위에 보인다.
FIXTURE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 html,body{{margin:0;padding:0}}
 .card{{width:1080px;height:1350px;position:relative;overflow:hidden;background:#eee;font-family:sans-serif}}
</style></head><body>
<div class="card" data-screen-label="01">
  <div id="front" style="position:absolute; left:200px; top:300px; width:300px; height:120px;
                         background:#2b6cb0; color:#fff; font-size:40px;">앞</div>
  <div id="wrap" style="padding-top:340px; padding-left:260px;">
    <div id="back" style="width:300px; height:120px; background:#999; color:#000; font-size:40px;">뒤</div>
  </div>
</div>
<script>{agent}</script>
</body></html>"""

# 두 요소가 겹치는 지점에서 실제로 어느 것이 위에 그려지는지 = elementFromPoint
PROBE = """() => {
  var f = document.getElementById('front').getBoundingClientRect();
  var b = document.getElementById('back').getBoundingClientRect();
  var x = Math.max(f.left, b.left) + 10;
  var y = Math.max(f.top, b.top) + 10;
  var hit = document.elementFromPoint(x, y);
  return {
    overlaps: !(f.right < b.left || b.right < f.left || f.bottom < b.top || b.bottom < f.top),
    onTop: hit ? (hit.id || hit.tagName) : null,
    frontPos: getComputedStyle(document.getElementById('front')).position,
    backPos: getComputedStyle(document.getElementById('back')).position
  };
}"""

POST = "(t) => window.postMessage(Object.assign({source:'pi-host'}, t), '*')"


async def main() -> int:
    agent = extract_agent_body()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.set_content(FIXTURE.format(agent=agent), wait_until="load")
        await pg.evaluate("document.fonts && document.fonts.ready")
        before = await pg.evaluate(PROBE)

        await pg.evaluate(POST, {"type": "SET_MODE", "mode": "edit"})
        await pg.wait_for_timeout(400)
        after = await pg.evaluate(PROBE)
        await b.close()

    print("승격 전:", before)
    print("승격 후:", after)

    assert before["overlaps"], "픽스처가 겹침을 만들지 못했다"
    kept = before["onTop"] == after["onTop"]
    print()
    print(f"  겹친 지점에서 위에 있는 것: 승격 전 '{before['onTop']}' → 승격 후 '{after['onTop']}'")
    print(f"  [{'OK' if kept else 'NG'}] 프리즈가 겹침 순서를 보존하나")
    if not kept:
        print("\nFAIL — 편집 모드에 들어가는 것만으로 앞뒤가 뒤바뀐다(뷰어 PNG와 달라진다).")
    return 0 if kept else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
