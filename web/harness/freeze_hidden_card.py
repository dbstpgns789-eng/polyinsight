# -*- coding: utf-8 -*-
"""편집 진입 시 카드 폭 붕괴(텍스트가 세로로 흐름) 회귀 하네스 — 2026-07-26.

증상: 편집 모드에 들어가면 어떤 카드의 텍스트가 한 글자씩 세로로 흐른다(폭이 0으로 붕괴).

가설: applyPaging()이 폰트 로딩 중이면 `card`를 클로저로 잡아 document.fonts.ready 후에
      freezeCard(card)를 돌린다. 그 사이 SET_PAGE가 오면 그 카드는 .pi-hidden(display:none)이
      된다. display:none 요소의 getBoundingClientRect()는 전부 0이므로 pinCollapsingContainers와
      promoteAll이 width:0/height:0을 인라인으로 박고, data-pi-frozen='1'까지 붙어 다시 freeze되지도
      않는다. 그 카드로 돌아오면 폭 0에서 한글이 한 글자씩 흘러 세로로 보인다.

이 경로는 사용자 조작 없이도 열린다 — page.tsx가 EDITOR_READY 직후 진입 카드를 SET_PAGE로 보낸다
(DeckEditor.tsx). 즉 SET_MODE(freeze 예약) → SET_PAGE(예약된 카드가 hidden) → 폰트 로드 → 붕괴.

실행: .venv/Scripts/python.exe web/harness/freeze_hidden_card.py   (레포 루트에서)
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


# 폰트 로딩을 우리가 제어한다 — 에이전트 주입 前에 패치해야 에이전트가 이 Promise를 쓴다.
FONT_GATE = """
<script>
(function () {
  var release;
  var gate = new Promise(function (r) { release = r; });
  window.__releaseFonts = function () { release(); };
  Object.defineProperty(document.fonts, 'ready', { get: function () { return gate; } });
  Object.defineProperty(document.fonts, 'status', { get: function () { return 'loading'; } });
})();
</script>
"""

FIXTURE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
 html,body{{margin:0;padding:0}}
 .card{{width:1080px;height:1350px;position:relative;overflow:hidden;font-family:sans-serif}}
</style>{gate}</head><body>
<div class="card" data-screen-label="01" style="background:#1d2b24;">
  <div style="position:absolute; top:300px; left:64px; right:64px;">
    <h1 id="title" style="font-size:88px; font-weight:900; color:#EDE6D5; line-height:1.18;">산성도를 읽는 구슬</h1>
    <p id="body" style="font-size:26px; color:#c9d0da; margin-top:24px;">새우껍질에서 뽑은 나노껍질로 셀룰로오스 구슬을 빚었다.</p>
  </div>
</div>
<div class="card" data-screen-label="02" style="background:#F4EEDF;">
  <div style="position:absolute; top:300px; left:64px; right:64px;">
    <h1 id="title2" style="font-size:72px; font-weight:900; color:#1c1c1e;">두 번째 카드</h1>
  </div>
</div>
<script>{agent}</script>
</body></html>"""

MEASURE = """() => {
  function box(id) {
    var el = document.getElementById(id);
    var r = el.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height), inlineW: el.style.width || '(none)' };
  }
  return { title: box('title'), body: box('body') };
}"""

POST = "(t) => window.postMessage(Object.assign({source:'pi-host'}, t), '*')"


async def main() -> int:
    agent = extract_agent_body()
    html = FIXTURE.format(agent=agent, gate=FONT_GATE)

    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.set_content(html, wait_until="load")

        before = await pg.evaluate(MEASURE)

        # 실제 진입 경로: SET_MODE 'edit'(freeze 예약) → SET_PAGE(예약된 카드가 hidden이 됨)
        await pg.evaluate(POST, {"type": "SET_MODE", "mode": "edit"})
        await pg.wait_for_timeout(50)
        await pg.evaluate(POST, {"type": "SET_PAGE", "index": 1})
        await pg.wait_for_timeout(50)

        # 이제 폰트 로드 완료 → 예약됐던 freeze(card0)가 hidden 상태에서 실행된다
        await pg.evaluate("window.__releaseFonts()")
        await pg.wait_for_timeout(200)

        # 1번 카드로 돌아온다 — 사용자가 보는 상태
        await pg.evaluate(POST, {"type": "SET_PAGE", "index": 0})
        await pg.wait_for_timeout(200)

        after = await pg.evaluate(MEASURE)
        await b.close()

    print("before:", before)
    print("after :", after)

    # 카드 폭 1080 - 좌우 패딩 64*2 = 952. 붕괴하면 0에 가까워진다.
    ok = after["title"]["w"] > 900 and after["body"]["w"] > 900
    if not ok:
        print("\nFAIL — 편집 진입 후 카드 폭이 붕괴했다(텍스트가 세로로 흐르는 증상).")
        print(f"  title  {before['title']['w']} -> {after['title']['w']} (inline width={after['title']['inlineW']})")
        print(f"  body   {before['body']['w']} -> {after['body']['w']} (inline width={after['body']['inlineW']})")
    else:
        print("\nPASS — 폭 유지됨.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
