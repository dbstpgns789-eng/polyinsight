# -*- coding: utf-8 -*-
"""글자가 요소 박스를 넘칠 때의 선택·클릭 하네스 — 2026-07-27.

제보: 텍스트가 안 잡힌다 / 선택 박스가 글자와 어긋난다 / 요소가 겹쳐 보인다.

원인(실측): line-height가 1보다 작으면(큰 제목을 타이트하게 붙이는 정상적 조판) 큰 한글의
  글리프가 라인박스 밖으로 나간다. 실측 예: font-size 104px, line-height 0.98 →
  요소 박스 204px인데 실제 글자는 253px(위 25px·아래 24px 초과).
  브라우저 클릭 판정과 선택 오버레이는 둘 다 '박스' 기준이라,
    · 튀어나온 글자를 눌러도 잡히지 않고
    · 선택 테두리가 보이는 글자와 어긋난다.

기대(피그마 관례): 피그마는 텍스트 프레임이 항상 글자를 감싸므로 프레임을 그려도 어긋나지
  않는다. 우리는 프레임 < 글자인 경우가 있으니 '박스 ∪ 글자범위'를 쓰면 같은 결과가 된다.

실행: .venv/Scripts/python.exe web/harness/glyph_overflow_select.py   (레포 루트에서)
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


# 실제 덱(test1 표지)은 104px · line-height 0.98 · Gowun Batang이고, 그 조합에서 글자가
# 박스를 위 25px·아래 24px 넘긴다. ★초과량은 폰트 메트릭에 좌우된다 — 같은 조건에서
# 시스템 serif는 2px밖에 안 넘친다(실측). 하네스가 웹폰트 다운로드에 의존하지 않도록
# line-height를 더 줄여 같은 상황(라인박스 < 글리프)을 시스템 폰트로 만든다.
FIXTURE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 html,body{{margin:0;padding:0}}
 .card{{width:1080px;height:1350px;position:relative;overflow:hidden;background:#e9d3a8;font-family:serif}}
</style></head><body>
<div class="card" data-screen-label="01">
  <div style="position:absolute; top:150px; left:64px; right:64px;">
    <div id="title" style="font-size:104px; font-weight:700; line-height:0.7; color:#2e2838;">
      막을 통과하면<br>구슬이 된다
    </div>
  </div>
</div>
<script>{agent}</script>
</body></html>"""

METRICS = """() => {
  var card = document.querySelector('[data-screen-label]');
  var cr = card.getBoundingClientRect();
  var t = document.getElementById('title');
  var br = t.getBoundingClientRect();
  var rng = document.createRange(); rng.selectNodeContents(t);
  var gr = rng.getBoundingClientRect();
  // 선택 오버레이 = 에이전트가 만든 테두리 박스(핸들·배지 제외)
  var ov = null;
  document.querySelectorAll('[data-pi-artifact]').forEach(function (e) {
    if (e.hasAttribute('data-pi-handle')) return;
    var s = getComputedStyle(e);
    if (s.display === 'none' || !e.style.borderWidth && s.borderTopWidth === '0px') return;
    var r = e.getBoundingClientRect();
    if (r.width > 100 && r.height > 40) ov = r;
  });
  return {
    box:   {top: Math.round(br.top - cr.top), bottom: Math.round(br.bottom - cr.top)},
    glyph: {top: Math.round(gr.top - cr.top), bottom: Math.round(gr.bottom - cr.top)},
    overlay: ov ? {top: Math.round(ov.top - cr.top), bottom: Math.round(ov.bottom - cr.top)} : null,
    // 에이전트가 실제로 무엇을 선택했는지는 SELECTED 메시지가 유일한 사실 소스다
    // (예전엔 첫 [data-eid] 요소를 봤는데, 그건 선택과 무관해 항상 통과하는 가짜 측정이었다)
    selectedId: (function () {
      var s = window.__lastSel;
      if (!s || !s.eid) return null;
      var el = document.querySelector('[data-eid="' + s.eid + '"]');
      return el ? (el.id || el.tagName) : null;
    })()
  };
}"""

LISTEN = """() => {
  window.__lastSel = null;
  window.addEventListener('message', function (e) {
    if (e.data && e.data.source === 'pi-deck' && e.data.type === 'SELECTED') window.__lastSel = e.data;
    if (e.data && e.data.source === 'pi-deck' && e.data.type === 'DESELECTED') window.__lastSel = null;
  });
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

        m0 = await pg.evaluate(METRICS)
        overflow_top = m0["box"]["top"] - m0["glyph"]["top"]

        # ① 박스 위로 튀어나온 글자를 클릭한다 — 보이는 글자니 잡혀야 한다
        card = await pg.locator("[data-screen-label]").bounding_box()
        hit_y = card["y"] + m0["glyph"]["top"] + 6      # 글자 최상단 바로 아래
        hit_x = card["x"] + 120                          # 첫 글자 '막' 위
        await pg.mouse.click(hit_x, hit_y)
        await pg.wait_for_timeout(250)
        after = await pg.evaluate(METRICS)
        await b.close()

    print(f"요소 박스   top={m0['box']['top']} bottom={m0['box']['bottom']}")
    print(f"실제 글자   top={m0['glyph']['top']} bottom={m0['glyph']['bottom']}  (위로 {overflow_top}px 초과)")
    print(f"선택 오버레이 {after['overlay']}")
    print(f"클릭으로 잡힌 것: {after['selectedId']}")

    assert overflow_top > 10, "픽스처가 글자 초과를 재현하지 못했다"
    hit_ok = after["selectedId"] == "title"
    ov = after["overlay"]
    cover_ok = bool(ov) and ov["top"] <= m0["glyph"]["top"] + 1 and ov["bottom"] >= m0["glyph"]["bottom"] - 1

    print()
    print(f"  [{'OK' if hit_ok else 'NG'}] 박스 밖으로 튀어나온 글자를 눌러 요소가 잡히나")
    print(f"  [{'OK' if cover_ok else 'NG'}] 선택 테두리가 실제 글자를 모두 감싸나")
    ok = hit_ok and cover_ok
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
