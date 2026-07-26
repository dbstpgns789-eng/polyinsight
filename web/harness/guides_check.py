# -*- coding: utf-8 -*-
"""정렬 가이드 강화 회귀 하네스 — 실 AGENT_BODY 주입.
검증 대상(2026-07-24 추가): ①선택 시 치수 배지(W×H), ②드래그 시 이웃 간격 측정(주황 숫자).
freeze_overlap.py와 동일 기법 — editorAgent.ts의 진짜 AGENT_BODY를 Chromium에 주입, 실제 마우스로
선택·드래그해 오버레이가 뜨는지 픽셀로 측정.

실행: <repo>/.venv/Scripts/python.exe web/harness/guides_check.py   (워크트리 루트에서)
종료코드 0=PASS, 1=FAIL.
"""
import asyncio, pathlib, sys, json
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
AGENT_TS = ROOT / "web" / "src" / "components" / "deck" / "editorAgent.ts"


def extract_agent_body() -> str:
    src = AGENT_TS.read_text(encoding="utf-8")
    marker = "const AGENT_BODY = `"
    start = src.index(marker) + len(marker)
    end = src.index("`;", start)
    body = src[start:end]
    body = body.replace("\\\\", "\\").replace("\\`", "`").replace("\\${", "${")
    return body


# 3개 절대배치 박스(카드 직계자식). A=드래그 대상, B=A 아래, C=A 오른쪽 → 드래그 시 하/우 간격 측정.
FIXTURE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 html,body{{margin:0;padding:0}} .card{{width:1080px;height:1350px;background:#F4EEDF;position:relative;overflow:hidden;font-family:sans-serif}}
</style></head><body>
<div class="card" data-screen-label="s1">
  <div id="a" style="position:absolute; left:100px; top:100px; width:300px; height:120px; background:#88aacc;"></div>
  <div id="b" style="position:absolute; left:100px; top:400px; width:300px; height:120px; background:#aacc88;"></div>
  <div id="c" style="position:absolute; left:600px; top:100px; width:200px; height:120px; background:#ccaa88;"></div>
</div>
<script>{agent}</script>
</body></html>"""

# 선택 시 치수 배지(body 소재, "W × H" 텍스트, 표시중) 탐지
DIM = """() => {
  var arts = document.querySelectorAll('[data-pi-artifact]');
  for (var i=0;i<arts.length;i++){ var t=(arts[i].textContent||'').trim();
    if(/^\\d+\\s*\\u00d7\\s*\\d+$/.test(t) && arts[i].style.display!=='none') return t; }
  return null;
}"""

# 드래그 중 카드 안 간격 배지(순수 숫자 텍스트) 수집
SPACING = """() => {
  var card = document.querySelector('[data-screen-label]');
  var arts = card.querySelectorAll('[data-pi-artifact]');
  var nums = [];
  for (var i=0;i<arts.length;i++){ var t=(arts[i].textContent||'').trim(); if(/^\\d+$/.test(t)) nums.push(t); }
  return nums;
}"""


async def main() -> int:
    agent = extract_agent_body()
    html = FIXTURE.format(agent=agent)
    fails = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.set_content(html, wait_until="load")
        await pg.evaluate("document.fonts.ready")
        await pg.evaluate("window.postMessage({source:'pi-host',type:'SET_MODE',mode:'edit'},'*')")
        await pg.wait_for_timeout(150)

        # ① 선택: A 중심 클릭 → 치수 배지
        await pg.mouse.click(250, 160)
        await pg.wait_for_timeout(60)
        dim = await pg.evaluate(DIM)
        print("dim badge on select:", dim)
        if not dim:
            fails.append("치수 배지 안 뜸")
        elif dim.replace(" ", "") != "300×120":
            fails.append("치수 배지 값 틀림: " + dim + " (기대 300 × 120)")

        # ② 드래그: A를 +30,+30 이동(B·C 여전히 이웃) → 간격 측정
        await pg.mouse.move(250, 160)
        await pg.mouse.down()
        await pg.mouse.move(270, 180, steps=3)
        await pg.mouse.move(280, 190, steps=3)
        await pg.wait_for_timeout(40)
        nums = await pg.evaluate(SPACING)
        print("spacing badges during drag:", nums)
        await pg.mouse.up()
        if len(nums) < 1:
            fails.append("드래그 중 간격 측정 안 뜸(하/우 이웃 있는데 0개)")

        # ③ 드래그 종료 후 간격/가이드 정리(잔상 없음)
        await pg.wait_for_timeout(40)
        left = await pg.evaluate(SPACING)
        print("spacing badges after drop:", left)
        if len(left) > 0:
            fails.append("드롭 후 간격 잔상 남음: " + str(left))

        await b.close()

    if fails:
        for f in fails:
            print("FAIL:", f)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
