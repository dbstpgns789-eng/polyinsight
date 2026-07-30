# -*- coding: utf-8 -*-
"""텍스트 상호작용 = 피그마 모델 하네스 — 2026-07-27.

요구(세훈, 피그마 화면 제시):
  · 텍스트 박스는 **어디를 잡아도** 통째로 선택돼 움직여야 한다.
  · 내용 수정은 **더블클릭**으로 들어간다.

고치기 전 문제:
  ① 부분 색상용 <span>("구슬"만 초록)을 클릭하면 그 span만 잡혔다(197x151). 제목을 옮기려고
     글자를 눌렀는데 두 글자만 잡히는 상태. 피그마는 부분 색상이 스타일 속성이라 별도 노드가
     안 생기고 늘 텍스트 전체가 잡힌다.
  ② 한 번 클릭만으로 편집 모드(contenteditable)에 들어가서, 선택 상태와 편집 상태가 구분되지
     않았다.

검사 항목
  1) span 글자를 클릭해도 텍스트 박스 전체가 선택된다
  2) 한 번 클릭은 선택까지만 — 편집 모드로 들어가지 않는다
  3) 더블클릭하면 편집 모드로 들어간다(contenteditable + 포커스)
  4) 선택 상태에서 드래그하면 요소가 움직인다(무회귀)

실행: .venv/Scripts/python.exe web/harness/figma_text_model.py   (레포 루트에서)
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


# 실제 덱 표지와 같은 구조 — 제목 안에 부분 색상 <span>
FIXTURE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 html,body{{margin:0;padding:0}}
 .card{{width:1080px;height:1350px;position:relative;overflow:hidden;background:#e9d3a8;font-family:serif}}
</style></head><body>
<div class="card" data-screen-label="01">
  <div style="position:absolute; top:150px; left:64px; right:64px;">
    <div id="title" style="font-size:104px; font-weight:700; line-height:1.1; color:#2e2838;">
      막을 통과하면<br><span id="green" style="color:#3f6a2c;">구슬</span>이 된다
    </div>
  </div>
</div>
<script>{agent}</script>
</body></html>"""

LISTEN = """() => {
  window.__lastSel = null;
  window.addEventListener('message', function (e) {
    if (!e.data || e.data.source !== 'pi-deck') return;
    if (e.data.type === 'SELECTED') window.__lastSel = e.data;
    if (e.data.type === 'DESELECTED') window.__lastSel = null;
  });
}"""

STATE = """() => {
  var s = window.__lastSel;
  var el = s && s.eid ? document.querySelector('[data-eid="' + s.eid + '"]') : null;
  var t = document.getElementById('title');
  var ce = document.querySelector('[contenteditable="true"]');
  return {
    selected: el ? (el.id || el.tagName.toLowerCase()) : null,
    editing: ce ? (ce.id || ce.tagName.toLowerCase()) : null,
    focused: document.activeElement ? (document.activeElement.id || document.activeElement.tagName.toLowerCase()) : null,
    top: t.style.top || '(flow)'
  };
}"""

POST = "(t) => window.postMessage(Object.assign({source:'pi-host'}, t), '*')"


async def main() -> int:
    agent = extract_agent_body()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.set_content(FIXTURE.format(agent=agent), wait_until="load")
        await pg.evaluate(LISTEN)
        await pg.evaluate("document.fonts && document.fonts.ready")
        await pg.evaluate(POST, {"type": "SET_MODE", "mode": "edit"})
        await pg.wait_for_timeout(300)

        green = await pg.locator("#green").bounding_box()
        gx, gy = green["x"] + green["width"] / 2, green["y"] + green["height"] / 2

        # ① 부분 색상 span 위를 한 번 클릭
        await pg.mouse.click(gx, gy)
        await pg.wait_for_timeout(250)
        one = await pg.evaluate(STATE)

        # ② 같은 자리를 더블클릭
        await pg.mouse.dblclick(gx, gy)
        await pg.wait_for_timeout(300)
        two = await pg.evaluate(STATE)

        # ③ 편집을 벗어난 뒤 선택 상태에서 드래그 → 요소 이동
        await pg.mouse.click(green["x"] + 700, green["y"] + 500)   # 빈 곳 = 편집 해제
        await pg.wait_for_timeout(200)
        await pg.mouse.click(gx, gy)
        await pg.wait_for_timeout(200)
        before_top = (await pg.evaluate(STATE))["top"]
        await pg.mouse.move(gx, gy)
        await pg.mouse.down()
        await pg.mouse.move(gx, gy - 100, steps=10)
        await pg.mouse.up()
        await pg.wait_for_timeout(250)
        moved = await pg.evaluate(STATE)
        await b.close()

    print("한 번 클릭 :", one)
    print("더블클릭   :", two)
    print("드래그 후  :", moved, f"(이전 top={before_top})")

    whole_ok = one["selected"] == "title"
    not_editing_ok = one["editing"] is None
    dbl_ok = two["editing"] == "title" and two["focused"] == "title"
    move_ok = moved["top"] != before_top

    print()
    print(f"  [{'OK' if whole_ok else 'NG'}] 부분색상 span을 눌러도 텍스트 박스 전체가 잡히나 -> {one['selected']}")
    print(f"  [{'OK' if not_editing_ok else 'NG'}] 한 번 클릭은 선택까지만인가(편집 진입 안 함) -> {one['editing']}")
    print(f"  [{'OK' if dbl_ok else 'NG'}] 더블클릭하면 편집 모드로 들어가나 -> {two['editing']}/{two['focused']}")
    print(f"  [{'OK' if move_ok else 'NG'}] 선택 상태 드래그로 요소가 움직이나 -> {before_top} → {moved['top']}")
    ok = whole_ok and not_editing_ok and dbl_ok and move_ok
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
