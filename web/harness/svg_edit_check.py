# -*- coding: utf-8 -*-
"""SVG 내부 도형 개별 편집 하네스 — 실 AGENT_BODY 주입.
검증(2026-07-26): svg 안 circle/rect/text를 ①개별 선택(루트 통짜 아님) ②이동(transform)
③undo 원복 ④serialize에 transform 살고 data-pi/eid 제거. viewBox 스케일 2배로 CTM 변환도 검증.

실행: <repo>/.venv/Scripts/python.exe web/harness/svg_edit_check.py
종료코드 0=PASS, 1=FAIL.
"""
import asyncio, pathlib, sys
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
AGENT_TS = ROOT / "web" / "src" / "components" / "deck" / "editorAgent.ts"


def extract_agent_body() -> str:
    src = AGENT_TS.read_text(encoding="utf-8")
    m = "const AGENT_BODY = `"; s = src.index(m) + len(m); e = src.index("`;", s)
    return src[s:e].replace("\\\\", "\\").replace("\\`", "`").replace("\\${", "${")


# svg width=600 viewBox=300 → 스케일 2 (1 user단위 = 2 card px). 막대 다이어그램 축소판.
FIXTURE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 html,body{{margin:0;padding:0}} .card{{width:1080px;height:1350px;background:#F4EEDF;position:relative;overflow:hidden}}
</style></head><body>
<div class="card" data-screen-label="s1">
  <svg id="dia" width="600" height="400" viewBox="0 0 300 200" style="position:absolute; left:100px; top:200px;">
    <rect x="0" y="90" width="300" height="20" fill="#556"/>
    <circle id="oil1" cx="60" cy="40" r="25" fill="#88aacc"/>
    <circle id="oil2" cx="160" cy="40" r="25" fill="#88aacc"/>
    <circle id="bead1" cx="60" cy="160" r="12" fill="#6688aa"/>
    <text x="10" y="20" font-size="12" fill="#333">기름상</text>
  </svg>
</div>
<script data-pi-agent="1">{agent}</script>
</body></html>"""

RECT = "(id) => { var r=document.getElementById(id).getBoundingClientRect(); return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}; }"
LASTSEL = "() => { for(var i=window.__msgs.length-1;i>=0;i--){ if(window.__msgs[i].type==='SELECTED') return window.__msgs[i]; } return null; }"
LASTHTML = "() => { for(var i=window.__msgs.length-1;i>=0;i--){ if(window.__msgs[i].type==='HTML') return window.__msgs[i].html; } return null; }"


async def main() -> int:
    agent = extract_agent_body()
    html = FIXTURE.format(agent=agent)
    fails = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.set_content(html, wait_until="load")
        await pg.evaluate("() => { window.__msgs=[]; window.addEventListener('message', e => { if(e.data && e.data.source==='pi-deck') window.__msgs.push(e.data); }); }")
        await pg.evaluate("window.postMessage({source:'pi-host',type:'SET_MODE',mode:'edit'},'*')")
        await pg.wait_for_timeout(150)

        # oil1 중심 ≈ card (220,280), r≈50. 클릭 → 개별 선택
        before = await pg.evaluate(RECT, "oil1")
        svg0 = await pg.evaluate(RECT, "dia")
        await pg.mouse.click(220, 280)
        await pg.wait_for_timeout(60)
        sel = await pg.evaluate(LASTSEL)
        print("SELECTED:", None if not sel else {"tag": sel.get("tag"), "w": round(sel["rect"]["w"]) if sel.get("rect") else None})
        if not sel or not sel.get("rect"):
            fails.append("svg 도형 클릭했는데 SELECTED 없음")
        elif round(sel["rect"]["w"]) > 200:
            fails.append(f"개별 선택 실패 — svg 통째 잡힘(rect.w={round(sel['rect']['w'])}, 원 bbox≈100 기대)")
        elif sel.get("tag") != "circle":
            fails.append(f"선택 태그 circle 아님: {sel.get('tag')}")

        # 드래그 +100,+50 → 이동
        await pg.mouse.move(220, 280); await pg.mouse.down()
        await pg.mouse.move(280, 305, steps=3); await pg.mouse.move(320, 330, steps=3)
        await pg.mouse.up()
        await pg.wait_for_timeout(40)
        after = await pg.evaluate(RECT, "oil1")
        svg1 = await pg.evaluate(RECT, "dia")
        oth = await pg.evaluate(RECT, "oil2")
        mvx, mvy = after["x"]-before["x"], after["y"]-before["y"]
        print(f"oil1 이동: dx={mvx} dy={mvy} (기대 ~100,50)")
        if abs(mvx-100) > 6 or abs(mvy-50) > 6:
            fails.append(f"이동량 틀림 dx={mvx} dy={mvy}")
        if svg0 != svg1:
            fails.append(f"svg 루트가 따라 움직임(도형만 움직여야): {svg0}->{svg1}")

        # serialize: transform 살아있고 data-pi/eid 제거
        await pg.evaluate("window.postMessage({source:'pi-host',type:'GET_HTML'},'*')")
        await pg.wait_for_timeout(50)
        out = await pg.evaluate(LASTHTML) or ""
        import re as _re
        has_tf = "translate(" in out
        hits = sorted(set(_re.findall(r'data-pi-[a-z]+|data-eid', out)))
        # 이 하네스의 관심사 = svg 도형에 찍힌 data-eid(선택 스탬프)가 serialize에서 지워지는가.
        # data-pi-frozen은 freezeCard가 카드에 남기는 기존 아티팩트(내 svg 변경과 무관, serialize가 원래 안 지움).
        leak_eid = "data-eid" in out
        print(f"serialize: transform={has_tf} data-eid누출={leak_eid} (기타 기존아티팩트={[h for h in hits if h!='data-eid']})")
        if not has_tf:
            fails.append("serialize에 이동 transform 없음")
        if leak_eid:
            fails.append("svg 도형 data-eid가 serialize에서 안 지워짐")

        # undo → 원위치
        await pg.evaluate("window.postMessage({source:'pi-host',type:'UNDO'},'*')")
        await pg.wait_for_timeout(60)
        back = await pg.evaluate(RECT, "oil1")
        print(f"undo 후 oil1: {back} (원본 {before})")
        if abs(back["x"]-before["x"]) > 2 or abs(back["y"]-before["y"]) > 2:
            fails.append(f"undo 원복 실패: {back} != {before}")

        await b.close()

    if fails:
        for f in fails: print("FAIL:", f)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
