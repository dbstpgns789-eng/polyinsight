# -*- coding: utf-8 -*-
"""편집 중 요소가 부모 박스 경계에서 잘리는지 — 2026-07-30.

제보: "스텝별로 직사각형 박스가 있는 것 같은데, 박스 안쪽에선 요소가 보이고 넘어가면 가려진다."

원인: 저작 모델이 카드 안 컨테이너(스텝 박스·카드형 패널)에 overflow:hidden을 준다.
  실측: 서버 덱 6개에서 내부 컨테이너 overflow:hidden이 6~9개씩. 렌더용으로는 옳다 — 그 박스가
  내용을 깔끔히 담는다. 그런데 편집기에서 요소를 그 박스 밖으로 끌면 **잘려서 사라진다.**
  사용자는 요소를 잃어버린 것처럼 느낀다(선택은 되어 있는데 화면에 안 보임).

기대: 편집 중에는 카드 안 어디로든 자유롭게 옮길 수 있어야 한다. 카드 프레임(1080x1350) 밖으로
  넘치는 것만 막으면 되고, **내부 컨테이너의 클리핑은 편집 중 해제**해야 한다.
  해제는 pageStyle(편집 모드 전용 <style>, data-pi-artifact라 serialize에서 제거)로 하므로
  저장 HTML과 렌더 PNG는 원본 그대로 유지된다.

실행: .venv/Scripts/python.exe web/harness/freeze_clipping.py   (레포 루트에서)
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


# 스텝 박스(overflow:hidden) 안의 요소 — 실제 덱과 같은 구조
FIXTURE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 html,body{{margin:0;padding:0}}
 .card{{width:1080px;height:1350px;position:relative;overflow:hidden;background:#eee;font-family:sans-serif}}
</style></head><body>
<div class="card" data-screen-label="01">
  <div id="step" style="position:absolute; left:150px; top:300px; width:400px; height:200px;
                        background:#fff; border-radius:16px; overflow:hidden;">
    <div id="chip" style="position:absolute; left:20px; top:20px; width:120px; height:60px;
                          background:#2b6cb0; color:#fff; font-size:28px;">12.</div>
  </div>
</div>
<script>{agent}</script>
</body></html>"""

# 칩을 스텝 박스 밖으로 내보낸 뒤, 그 자리에서 실제로 보이는지(=클릭이 닿는지) 본다.
MOVE_OUT_AND_PROBE = """() => {
  var chip = document.getElementById('chip');
  var step = document.getElementById('step');
  chip.style.left = '330px';   // 박스(width 400) 오른쪽 밖으로 절반 넘김
  var r = chip.getBoundingClientRect();
  var sr = step.getBoundingClientRect();
  var x = sr.right + 20;       // 박스 바깥이면서 칩 위인 지점
  var y = r.top + r.height / 2;
  var hit = document.elementFromPoint(x, y);
  return {
    outsideX: Math.round(x), chipRight: Math.round(r.right), stepRight: Math.round(sr.right),
    visibleOutside: !!(hit && hit.id === 'chip'),
    stepOverflow: getComputedStyle(step).overflow
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

        await pg.evaluate(POST, {"type": "SET_MODE", "mode": "edit"})
        await pg.wait_for_timeout(400)
        res = await pg.evaluate(MOVE_OUT_AND_PROBE)
        await b.close()

    print("스텝 박스 overflow :", res["stepOverflow"])
    print(f"칩 오른쪽 끝 {res['chipRight']} / 박스 오른쪽 끝 {res['stepRight']}"
          f" → 박스 밖 {res['outsideX']} 지점 검사")
    print()
    ok = res["visibleOutside"]
    print(f"  [{'OK' if ok else 'NG'}] 박스 밖으로 나간 부분이 편집 중에 보이나")
    if not ok:
        print("\nFAIL — 스텝 박스 경계에서 잘린다. 요소를 옮기면 사라진 것처럼 보인다.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
