# -*- coding: utf-8 -*-
"""텍스트 범위 선택(드래그로 긁기) 하네스 — 2026-07-26.

증상(제보): 텍스트를 드래그해서 긁고 싶은데 요소가 잡혀 끌린다.

원인: onMouseDown이 이동 임계(3px)를 넘으면 무조건 요소 드래그로 전환하면서
      clearEditable() + getSelection().removeAllRanges()로 텍스트 선택을 지운다.
      텍스트를 긁으려면 반드시 3px 이상 움직여야 하므로 범위 선택이 구조적으로 불가능했다.

기대 동작(Figma·Canva 관례): 이미 편집 중인 텍스트를 다시 끌면 텍스트 범위 선택이고,
      요소는 움직이지 않는다. 옮기고 싶으면 편집을 벗어난 뒤(딴 데 클릭) 끈다.

이 하네스는 두 가지를 함께 지킨다.
  1) 편집 중 드래그 → 텍스트가 선택되고 요소는 제자리
  2) 편집 아닐 때 드래그 → 요소가 이동(기존 기능 무회귀)

★headless로 못 돈다. Chromium headless에서는 마우스 드래그 텍스트 선택이 아예 동작하지 않는다
  (에이전트 없는 순수 contenteditable 대조군으로 확인 — headless는 '', headed는 선택됨).
  그리고 mouse.move(steps=N)로도 안 된다. 개별 move 호출 사이에 짧은 대기가 있어야 한다.
  그래서 창을 띄운다. CI가 아니라 로컬 검증용 도구다.

실행: .venv/Scripts/python.exe web/harness/text_drag_select.py   (레포 루트에서)
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


FIXTURE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 html,body{{margin:0;padding:0}}
 .card{{width:1080px;height:1350px;position:relative;overflow:hidden;background:#fff;font-family:sans-serif}}
</style></head><body>
<div class="card" data-screen-label="01">
  <div style="position:absolute; top:200px; left:100px; width:800px;">
    <p id="para" style="font-size:40px; line-height:1.5; color:#111;">
      가나다라마바사아자차카타파하 배경 문장이다
    </p>
  </div>
  <div style="position:absolute; top:600px; left:100px;">
    <p id="other" style="font-size:30px; color:#333;">다른 문단</p>
  </div>
</div>
<script>{agent}</script>
</body></html>"""

STATE = """() => {
  var p = document.getElementById('para');
  var sel = window.getSelection();
  return { left: p.style.left || '(none)', top: p.style.top || '(none)',
           selected: sel ? String(sel.toString()).trim() : '' };
}"""

POST = "(t) => window.postMessage(Object.assign({source:'pi-host'}, t), '*')"


async def drag(pg, x0, y, dx, dy):
    """텍스트 선택이 걸리는 드래그 — 개별 move + 대기(steps= 로는 선택이 안 잡힌다)."""
    await pg.mouse.move(x0, y)
    await pg.mouse.down()
    n = 24
    for i in range(1, n + 1):
        await pg.mouse.move(x0 + dx * i / n, y + dy * i / n)
        await pg.wait_for_timeout(8)
    await pg.mouse.up()
    await pg.wait_for_timeout(180)


async def main() -> int:
    agent = extract_agent_body()
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=False)
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.set_content(FIXTURE.format(agent=agent), wait_until="load")
        await pg.evaluate("document.fonts.ready")
        await pg.evaluate(POST, {"type": "SET_MODE", "mode": "edit"})
        await pg.wait_for_timeout(250)

        box = await pg.locator("#para").bounding_box()
        y = box["y"] + box["height"] / 2
        x0 = box["x"] + 30

        # ① 한 번 클릭 → 선택 + 편집 진입
        await pg.mouse.click(x0, y)
        await pg.wait_for_timeout(120)
        after_click = await pg.evaluate(STATE)

        # ② 편집 중인 텍스트를 다시 끈다 → 범위 선택이어야 하고 요소는 제자리
        await drag(pg, x0, y, 260, 0)
        after_drag = await pg.evaluate(STATE)

        # ③ 무회귀: 편집을 벗어난 뒤 끌면 요소가 이동해야 한다
        await pg.mouse.click(box["x"] + 900, box["y"] + 700)   # 딴 데 클릭 = 편집 해제
        await pg.wait_for_timeout(120)
        await drag(pg, x0, y, 0, -120)
        after_move = await pg.evaluate(STATE)
        await b.close()

    print("클릭 후      :", after_click)
    print("편집중 드래그:", after_drag)
    print("해제 후 드래그:", after_move)

    text_ok = bool(after_drag["selected"])
    stay_ok = after_drag["left"] == after_click["left"] and after_drag["top"] == after_click["top"]
    move_ok = after_move["top"] != after_drag["top"]

    print()
    print(f"  [{'OK' if text_ok else 'NG'}] 편집 중 드래그가 텍스트를 선택했나 -> {after_drag['selected']!r}")
    print(f"  [{'OK' if stay_ok else 'NG'}] 그때 요소가 제자리였나")
    print(f"  [{'OK' if move_ok else 'NG'}] 편집 해제 후 드래그는 여전히 요소를 옮기나(무회귀)")
    ok = text_ok and stay_ok and move_ok
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
