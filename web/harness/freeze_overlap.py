# -*- coding: utf-8 -*-
"""편집 프리즈(freezeCard) 회귀 하네스 — 실 AGENT_BODY 주입.
web은 vitest(jsdom)뿐이라 레이아웃 버그(요소 겹침)를 못 잡는다. 이 하네스는 editorAgent.ts의
**진짜 AGENT_BODY**를 추출해 실제 Chromium에 주입하고, 편집 모드(SET_MODE 'edit')로 freeze를 돌린 뒤
카드 자식들이 겹치지 않고 픽셀 무이동인지 측정한다.

회귀 대상 버그(2026-07-13): bottom-앵커 + height:auto 컨테이너(마감 크레딧 카드)의 자식을 절대배치로
승격하면 컨테이너가 붕괴→윗변 하강→자식이 압축·겹침. 수정=pinCollapsingContainers(승격 前 부모 박스 고정).

실행: .venv/Scripts/python.exe web/harness/freeze_overlap.py   (레포 루트에서)
종료코드 0=PASS, 1=FAIL.
"""
import asyncio, pathlib, sys
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
AGENT_TS = ROOT / "web" / "src" / "components" / "deck" / "editorAgent.ts"


def extract_agent_body() -> str:
    src = AGENT_TS.read_text(encoding="utf-8")
    marker = "const AGENT_BODY = `"
    start = src.index(marker) + len(marker)
    end = src.index("`;", start)
    body = src[start:end]
    # 템플릿 리터럴 이스케이프 해제 → 런타임 JS
    body = body.replace("\\\\", "\\").replace("\\`", "`").replace("\\${", "${")
    return body


# 마감 크레딧 카드 재현 fixture: bottom-앵커 + height:auto 컨테이너, 자식은 일반 흐름.
FIXTURE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 html,body{{margin:0;padding:0}} .card{{width:1080px;height:1350px;background:#F4EEDF;position:relative;overflow:hidden;font-family:sans-serif}}
</style></head><body>
<div class="card" data-screen-label="closing">
  <div style="position:absolute; top:470px; left:64px; right:64px; text-align:center;">
    <h2 id="t1" style="font-size:46px; font-weight:900; line-height:1.16;">파괴 없이 만든 미세구슬,<br>플라스틱만큼 단단하고</h2>
    <p id="t2" style="font-size:20px; line-height:1.6; margin-top:22px;">전기방사로 만든 마이크로비드가 미세플라스틱을 대체합니다.</p>
  </div>
  <div style="position:absolute; bottom:150px; left:64px; right:64px; background:#1c1c1e; border-radius:10px; padding:40px 44px;">
    <div id="c1" style="color:#e8a13c; font-size:15px; font-weight:700; margin-bottom:14px;">ORIGINAL RESEARCH · CELLULOSE (2024)</div>
    <p id="c2" style="color:#f2f0ec; font-size:20px; line-height:1.4;">Fabrication of composite microbeads consisting of cellulose and covalent organic nanosheets</p>
    <p id="c3" style="color:#b0aea9; font-size:17px; line-height:1.55; margin-top:18px;">Su Jin Ryu · Seungjun Kim ·<br>Dong Wook Kim · Myungwoong Kim · Hoik Lee</p>
    <div id="c4" style="height:1px; background:#3a3a3d; margin:20px 0;"></div>
    <p id="c5" style="color:#8a8a8e; font-size:15px;">한국생산기술연구원<br>DOI 10.1007/s10570-024-05757-4</p>
  </div>
</div>
<script>{agent}</script>
</body></html>"""

IDS = ["t1", "t2", "c1", "c2", "c3", "c4", "c5"]
CREDIT = ["c1", "c2", "c3", "c4", "c5"]

MEASURE = """() => {
  function top(id){ var r=document.getElementById(id).getBoundingClientRect(); return {top:Math.round(r.top),bottom:Math.round(r.bottom)}; }
  function overlaps(ids){ var bad=[]; for(var i=0;i<ids.length;i++)for(var j=i+1;j<ids.length;j++){ var a=document.getElementById(ids[i]).getBoundingClientRect(), b=document.getElementById(ids[j]).getBoundingClientRect(); if(a.top<b.bottom-1 && b.top<a.bottom-1) bad.push(ids[i]+'x'+ids[j]); } return bad; }
  var o={}; %s.forEach(function(id){o[id]=top(id);});
  return {tops:o, credit:overlaps(%s)};
}"""


async def main() -> int:
    import json
    agent = extract_agent_body()
    html = FIXTURE.format(agent=agent)
    measure = MEASURE % (json.dumps(IDS), json.dumps(CREDIT))
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.set_content(html, wait_until="load")
        await pg.evaluate("document.fonts.ready")
        before = await pg.evaluate(measure)
        # 실제 편집 진입 경로: 부모→iframe SET_MODE 'edit' → applyPaging → freezeCard
        await pg.evaluate("window.postMessage({source:'pi-host',type:'SET_MODE',mode:'edit'},'*')")
        await pg.evaluate("document.fonts.ready")
        await pg.wait_for_timeout(200)  # freeze(폰트 로드 후 async) 정착 대기
        after = await pg.evaluate(measure)
        await b.close()

    moved = {k: after["tops"][k]["top"] - before["tops"][k]["top"] for k in IDS}
    overlap = after["credit"]
    print("before credit overlaps:", before["credit"])
    print("after  credit overlaps:", overlap)
    print("moved (after-before top):", moved)
    ok = (not overlap) and all(abs(v) <= 1 for v in moved.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
