"""
경량 editorAgent 런타임 하네스 (Phase 3e 검증용).

editorAgent.ts에서 AGENT_BODY 문자열을 추출해, 합성 덱 HTML(1080x1350 카드 2개,
각 카드에 직계자식 블록 3개) 위 최상위 문서에 <script>로 주입한다. host<->agent
통신은 window.postMessage(최상위 문서라 parent===window). 마우스는 Playwright 합성
이벤트(스케일 없음 → 자연좌표=클라이언트좌표).

풀스택(uvicorn/next/인증) 없이 순수 에이전트 로직(선택/마퀴/다중이동/정렬/직렬화/undo)만
빠르고 안정적으로 검증한다. 저장경로(PATCH/PNG)는 범위 밖 — 마지막에 풀스택 1회.

사용:
  python deck_harness.py          # 베이스라인(현재 구현) 스모크
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENT_TS = REPO / "web" / "src" / "components" / "deck" / "editorAgent.ts"


def extract_agent_body() -> str:
    src = AGENT_TS.read_text(encoding="utf-8")
    # const AGENT_BODY = `...`;  — 첫 백틱과 마지막 백틱 사이
    i = src.index("`")
    j = src.rindex("`")
    body = src[i + 1 : j]
    # 외부 템플릿 리터럴의 이중 이스케이프(\\n)를 단일(\n=백슬래시+n 문자)로 되돌려
    # 번들러가 내보내는 것과 동일하게. (파일엔 백슬래시2+n)
    body = body.replace("\\\\", "\\")
    return body


# 합성 덱: 카드 2개. 각 카드는 position:relative 1080x1350, 직계자식 블록 3개(flow).
# 블록은 텍스트 리프(직접 편집 대상)이자 이동/정렬 대상.
def build_deck() -> str:
    # 카드1: flow 블록 3개(같은 폭) — 베이스라인 promote·텍스트편집·다중이동 검증.
    def flow_block(label, color):
        return (
            f'<div style="height:140px; margin:0 0 40px 0; padding:24px; '
            f'background:{color}; color:#fff; font-size:36px; border-radius:8px;">{label}</div>'
        )

    # 카드2: absolute 블록 3개(좌표·폭 제각각) — 정렬·분배·수치 검증.
    def abs_block(label, l, t, w, h, color):
        return (
            f'<div style="position:absolute; left:{l}px; top:{t}px; width:{w}px; height:{h}px; '
            f'padding:20px; background:{color}; color:#fff; font-size:30px; border-radius:8px;">{label}</div>'
        )

    card1_blocks = (
        flow_block("카드1 블록A", "#2F6F4E")
        + flow_block("카드1 블록B", "#3A5BA0")
        + flow_block("카드1 블록C", "#A0453A")
    )
    card2_blocks = (
        abs_block("카드2 A", 100, 100, 300, 120, "#2F6F4E")
        + abs_block("카드2 B", 500, 300, 200, 120, "#3A5BA0")
        + abs_block("카드2 C", 250, 550, 400, 120, "#A0453A")
    )

    def card(n, inner):
        return (
            f'<div data-screen-label="0{n}" style="width:1080px; height:1350px; '
            f'box-sizing:border-box; background:#0A0E1A; color:#EAF0FF; padding:90px 84px; '
            f'display:block; position:relative; overflow:hidden;">{inner}</div>'
        )

    return (
        "<!DOCTYPE html><html lang=ko><head><meta charset=utf-8>"
        "<style>*{box-sizing:border-box}body{margin:0;background:#05070f;"
        "padding:60px;display:flex;flex-direction:column;gap:60px;align-items:flex-start}</style>"
        "</head><body>" + card(1, card1_blocks) + card(2, card2_blocks) + "</body></html>"
    )


COLLECTOR = """
window.__hostMsgs = [];
window.addEventListener('message', function(e){
  if (e.data && e.data.source === 'pi-deck') window.__hostMsgs.push(e.data);
});
"""


def make_page(pw):
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": 1240, "height": 3000})
    agent = extract_agent_body()
    deck = build_deck()
    html = deck.replace(
        "</body>",
        f"<script>{COLLECTOR}</script><script data-pi-agent=1>{agent}</script></body>",
    )
    page.set_content(html, wait_until="load")
    page.wait_for_function("() => window.__piAgent === true", timeout=5000)
    host(page, "SET_MODE", mode="edit")
    return browser, page


def host(page, type_, **payload):
    page.evaluate(
        "(m) => window.postMessage(m, '*')",
        {"source": "pi-host", "type": type_, **payload},
    )


def msgs(page, type_=None):
    all_ = page.evaluate("() => window.__hostMsgs")
    return [m for m in all_ if (type_ is None or m.get("type") == type_)]


def last(page, type_):
    ms = msgs(page, type_)
    return ms[-1] if ms else None


def clear_msgs(page):
    page.evaluate("() => { window.__hostMsgs = []; }")


def wait_msg(page, type_, timeout=3000):
    """type_ 메시지가 수집될 때까지 대기 후 마지막 것 반환(없으면 None)."""
    try:
        page.wait_for_function(
            "(t) => window.__hostMsgs.some(m => m.type === t)", arg=type_, timeout=timeout
        )
    except Exception:
        return None
    return last(page, type_)


def block_info(page, card_idx, block_idx):
    """card_idx(0/1), block_idx(0..2) 블록의 style·rect 반환."""
    return page.evaluate(
        """([ci, bi]) => {
      const cards = document.querySelectorAll('[data-screen-label]');
      const card = cards[ci];
      const blocks = Array.from(card.children).filter(
        c => !c.hasAttribute('data-pi-artifact') && !(c.hasAttribute && c.hasAttribute('data-pi-overlay')) && c.tagName==='DIV'
      );
      const el = blocks[bi];
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {
        position: el.style.position||'', left: el.style.left||'', top: el.style.top||'',
        width: el.style.width||'', height: el.style.height||'',
        vx: r.left, vy: r.top, vw: r.width, vh: r.height,
        text: (el.textContent||'').slice(0,20)
      };
    }""",
        [card_idx, block_idx],
    )


def drag(page, x1, y1, x2, y2, steps=8):
    page.mouse.move(x1, y1)
    page.mouse.down()
    page.mouse.move(x2, y2, steps=steps)
    page.mouse.up()


def center(page, ci, bi):
    b = block_info(page, ci, bi)
    return b["vx"] + b["vw"] / 2, b["vy"] + b["vh"] / 2


def shift_click(page, x, y):
    page.keyboard.down("Shift")
    page.mouse.click(x, y)
    page.keyboard.up("Shift")


def card_rect(page, ci):
    return page.evaluate(
        "(ci) => { const c = document.querySelectorAll('[data-screen-label]')[ci]; const r = c.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height}; }",
        ci,
    )


def goto_card(page, ci):
    """편집 모드 페이징(3f): 조작·측정 전에 해당 카드로 페이지 이동(그 카드만 표시)."""
    host(page, "SET_PAGE", index=ci)
    page.wait_for_timeout(120)


def card_hidden(page, ci):
    return page.evaluate(
        "(ci) => document.querySelectorAll('[data-screen-label]')[ci].classList.contains('pi-hidden')",
        ci,
    )


def get_html(page):
    clear_msgs(page)
    host(page, "GET_HTML")
    page.wait_for_function(
        "() => window.__hostMsgs.some(m => m.type === 'HTML')", timeout=3000
    )
    return last(page, "HTML")["html"]


# ── 베이스라인(3d) 스모크 ─────────────────────────────────────────────
def test_baseline():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, page = make_page(pw)
        results = []

        def check(name, cond):
            results.append((name, bool(cond)))

        # 1) 카드1 블록A 클릭 → SELECTED
        b0 = block_info(page, 0, 0)
        cx, cy = b0["vx"] + b0["vw"] / 2, b0["vy"] + b0["vh"] / 2
        clear_msgs(page)
        page.mouse.click(cx, cy)
        sel = wait_msg(page, "SELECTED")
        check("클릭→SELECTED", sel is not None)

        # 2) 드래그 → position:absolute 승격 + left/top 변경
        clear_msgs(page)
        drag(page, cx, cy, cx + 120, cy + 80)
        hist = wait_msg(page, "HISTORY_STATE")
        b0b = block_info(page, 0, 0)
        check("드래그→absolute 승격", b0b["position"] == "absolute")
        check("드래그→left 설정", b0b["left"] != "")
        check("드래그→HISTORY canUndo", (hist or {}).get("canUndo") is True)

        # 3) undo → 흐름 복원(position 제거)
        clear_msgs(page)
        host(page, "UNDO")
        page.wait_for_timeout(150)
        b0c = block_info(page, 0, 0)
        check("undo→position 복원", b0c["position"] == "")

        # 4) 직렬화 청결성 — data-pi-* 아티팩트 0, data-screen-label 2개 유지
        html = get_html(page)
        check("serialize: data-pi 아티팩트 0", "data-pi-" not in html)
        check("serialize: contenteditable 0", "contenteditable" not in html)
        check("serialize: data-screen-label 2개", html.count("data-screen-label") == 2)

        browser.close()

        print("\n=== 베이스라인(3d) 스모크 ===")
        ok = True
        for name, passed in results:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            ok = ok and passed
        print(f"결과: {'ALL PASS' if ok else 'FAIL 있음'}")
        return ok


def test_multiselect():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, page = make_page(pw)
        results = []

        def check(name, cond):
            results.append((name, bool(cond)))

        # 1) Shift클릭 2개 → count=2
        ax, ay = center(page, 0, 0)
        bx, by = center(page, 0, 1)
        clear_msgs(page)
        page.mouse.click(ax, ay)
        wait_msg(page, "SELECTED")
        shift_click(page, bx, by)
        page.wait_for_timeout(120)
        sel = last(page, "SELECTED")
        check("shift클릭 → count=2", sel and sel.get("count") == 2)
        check("shift클릭 → tag '(다중 2)'", sel and "다중" in (sel.get("tag") or ""))

        # 2) 페이지 이동(SET_PAGE) → 카드2만 표시 + 선택 해제(3f R3)
        clear_msgs(page)
        host(page, "SET_PAGE", index=1)
        page.wait_for_timeout(120)
        check("페이지 이동 → DESELECTED", last(page, "DESELECTED") is not None)
        check("페이지 이동 → 카드2 표시·카드1 숨김", (not card_hidden(page, 1)) and card_hidden(page, 0))
        goto_card(page, 0)  # 이후 테스트 위해 카드1로 복귀

        # 3) 마퀴 드래그(카드1 빈영역→블록들 가로지르기) → 다중 선택
        cr = card_rect(page, 0)
        x1, y1 = cr["x"] + 40, cr["y"] + cr["h"] - 120   # 카드1 하단 빈영역
        x2, y2 = cr["x"] + cr["w"] - 40, cr["y"] + 120   # 상단 블록 위
        clear_msgs(page)
        drag(page, x1, y1, x2, y2, steps=10)
        page.wait_for_timeout(120)
        sel = last(page, "SELECTED")
        check("마퀴 → count>=2", sel and sel.get("count", 0) >= 2)

        # 4) 다중 이동: A,B 선택 후 A 드래그 → 둘 다 같은 델타 이동, undo 1회 전원 복원
        ax, ay = center(page, 0, 0)
        page.mouse.click(ax, ay)
        wait_msg(page, "SELECTED")
        bx, by = center(page, 0, 1)
        shift_click(page, bx, by)
        page.wait_for_timeout(120)
        a0 = block_info(page, 0, 0)
        b0 = block_info(page, 0, 1)
        clear_msgs(page)
        drag(page, a0["vx"] + a0["vw"] / 2, a0["vy"] + a0["vh"] / 2,
             a0["vx"] + a0["vw"] / 2 + 100, a0["vy"] + a0["vh"] / 2 + 60)
        wait_msg(page, "HISTORY_STATE")
        a1 = block_info(page, 0, 0)
        b1 = block_info(page, 0, 1)
        da = a1["vx"] - a0["vx"]
        db = b1["vx"] - b0["vx"]
        check("다중이동: A 이동", abs(da) > 20)
        check("다중이동: B도 같은 델타(±3px)", abs(da - db) <= 3)
        # undo 1회 → 둘 다 flow 복원
        clear_msgs(page)
        host(page, "UNDO")
        page.wait_for_timeout(150)
        a2 = block_info(page, 0, 0)
        b2 = block_info(page, 0, 1)
        check("undo 1회 → A position 복원", a2["position"] == "")
        check("undo 1회 → B position 복원", b2["position"] == "")

        # 5) 직렬화 청결(마퀴/집합박스 잔재 0)
        html = get_html(page)
        check("serialize: 아티팩트 0", "data-pi-" not in html and "contenteditable" not in html)

        browser.close()
        print("\n=== 다중선택/이동(3e-2·3e-3) ===")
        ok = True
        for name, passed in results:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            ok = ok and passed
        print(f"결과: {'ALL PASS' if ok else 'FAIL 있음'}")
        return ok


def pxnum(s):
    try:
        return float(str(s).replace("px", ""))
    except Exception:
        return None


def test_align_numeric_textundo():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, page = make_page(pw)
        results = []

        def check(name, cond):
            results.append((name, bool(cond)))

        def sel_card2_all():
            goto_card(page, 1)   # 3f: 카드2로 페이지 이동해야 조작 가능
            ax, ay = center(page, 1, 0)
            page.mouse.click(ax, ay); wait_msg(page, "SELECTED")
            for bi in (1, 2):
                bx, by = center(page, 1, bi); shift_click(page, bx, by)
            page.wait_for_timeout(120)

        # A) 정렬(왼쪽): 카드2 A/B/C(left 100/500/250) → 전부 minx=100
        sel_card2_all()
        clear_msgs(page); host(page, "ALIGN", axis="left"); wait_msg(page, "HISTORY_STATE")
        lefts = [pxnum(block_info(page, 1, i)["left"]) for i in range(3)]
        check("정렬 왼쪽 → 전부 left=100", all(l is not None and abs(l - 100) <= 1 for l in lefts))
        host(page, "UNDO"); page.wait_for_timeout(150)
        check("정렬 undo → B left=500 복원", abs((pxnum(block_info(page, 1, 1)["left"]) or 0) - 500) <= 1)

        # B) 분배(세로): 3개 top 균등간격(edge-to-edge). 정렬 후 gap 동일
        sel_card2_all()
        clear_msgs(page); host(page, "DISTRIBUTE", axis="v"); wait_msg(page, "HISTORY_STATE")
        items = sorted(
            [(pxnum(block_info(page, 1, i)["top"]), block_info(page, 1, i)["vh"]) for i in range(3)],
            key=lambda x: x[0],
        )
        gap1 = items[1][0] - (items[0][0] + items[0][1])
        gap2 = items[2][0] - (items[1][0] + items[1][1])
        check("분배 세로 → 인접 간격 균등(±2px)", abs(gap1 - gap2) <= 2)
        host(page, "UNDO"); page.wait_for_timeout(150)

        # C) 수치 단일: 카드2 A left=400
        goto_card(page, 1)
        ax, ay = center(page, 1, 0)
        page.mouse.click(ax, ay); wait_msg(page, "SELECTED")
        clear_msgs(page); host(page, "SET_RECT", left=400); wait_msg(page, "HISTORY_STATE")
        check("수치 단일 left=400", abs((pxnum(block_info(page, 1, 0)["left"]) or 0) - 400) <= 1)
        host(page, "UNDO"); page.wait_for_timeout(150)
        check("수치 단일 undo → left=100 복원", abs((pxnum(block_info(page, 1, 0)["left"]) or 0) - 100) <= 1)

        # D) 수치 다중: A,B 선택 → 집합 좌상단 left=50 (A left100,B left500 → minx100 → +? => 50)
        goto_card(page, 1)
        ax, ay = center(page, 1, 0)
        page.mouse.click(ax, ay); wait_msg(page, "SELECTED")
        bx, by = center(page, 1, 1); shift_click(page, bx, by); page.wait_for_timeout(120)
        clear_msgs(page); host(page, "SET_RECT", left=50); wait_msg(page, "HISTORY_STATE")
        la = pxnum(block_info(page, 1, 0)["left"]); lb = pxnum(block_info(page, 1, 1)["left"])
        check("수치 다중 → 집합 minx=50", abs(min(la, lb) - 50) <= 1)
        check("수치 다중 → 상대간격 보존(400)", abs((lb - la) - 400) <= 2)
        host(page, "UNDO"); page.wait_for_timeout(150)

        # E) 텍스트 undo 보편성: 카드1 텍스트 편집 → UNDO 1회에 원문 복원
        goto_card(page, 0)
        cx, cy = center(page, 0, 0)
        orig = block_info(page, 0, 0)["text"]
        page.mouse.click(cx, cy); wait_msg(page, "SELECTED")
        page.keyboard.type("ZZZ")
        page.wait_for_timeout(80)
        changed = block_info(page, 0, 0)["text"]
        check("텍스트 입력 반영", changed != orig)
        clear_msgs(page); host(page, "UNDO"); page.wait_for_timeout(150)
        restored = block_info(page, 0, 0)["text"]
        check("텍스트 UNDO → 원문 복원", restored == orig)

        # F) 직렬화 청결
        html = get_html(page)
        check("serialize: 아티팩트 0", "data-pi-" not in html and "contenteditable" not in html)

        browser.close()
        print("\n=== 정렬/분배/수치/텍스트undo(3e-4·5·6) ===")
        ok = True
        for name, passed in results:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            ok = ok and passed
        print(f"결과: {'ALL PASS' if ok else 'FAIL 있음'}")
        return ok


def test_undo_universality():
    """스펙 검증 #6: (텍스트수정 → 다중이동 → 정렬) 혼합 → 역순 완전 복원.
    + 버튼(host UNDO)과 키보드(Ctrl+Z) 경로 동치."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, page = make_page(pw)
        results = []

        def check(name, cond):
            results.append((name, bool(cond)))

        # 원본 스냅샷
        t_orig = block_info(page, 0, 0)["text"]
        c1a_pos = block_info(page, 0, 0)["position"]        # '' (flow)
        c2b_left = pxnum(block_info(page, 1, 1)["left"])     # 500

        # 1) 텍스트 수정(카드1 A)
        cx, cy = center(page, 0, 0)
        page.mouse.click(cx, cy); wait_msg(page, "SELECTED")
        page.keyboard.type("ZZZ"); page.wait_for_timeout(80)

        # 2) 다중 이동(카드1 A+B)
        ax, ay = center(page, 0, 0)
        page.mouse.click(ax, ay); wait_msg(page, "SELECTED")
        bx, by = center(page, 0, 1); shift_click(page, bx, by); page.wait_for_timeout(100)
        a0 = block_info(page, 0, 0)
        drag(page, a0["vx"] + 30, a0["vy"] + 30, a0["vx"] + 130, a0["vy"] + 90)
        wait_msg(page, "HISTORY_STATE")

        # 3) 정렬(카드2 A+B+C, 왼쪽) — 카드2로 페이지 이동
        goto_card(page, 1)
        px, py = center(page, 1, 0)
        page.mouse.click(px, py); wait_msg(page, "SELECTED")
        for bi in (1, 2):
            sx, sy = center(page, 1, bi); shift_click(page, sx, sy)
        page.wait_for_timeout(100)
        clear_msgs(page); host(page, "ALIGN", axis="left"); wait_msg(page, "HISTORY_STATE")
        check("정렬 적용됨(C2 B left=100)", abs((pxnum(block_info(page, 1, 1)["left"]) or 0) - 100) <= 1)

        # UNDO 1 (키보드 Ctrl+Z) → 정렬 되돌림
        page.keyboard.press("Control+z"); page.wait_for_timeout(150)
        check("Ctrl+Z 1 → 정렬 복원(C2 B left=500)", abs((pxnum(block_info(page, 1, 1)["left"]) or 0) - c2b_left) <= 1)

        # UNDO 2 (버튼 host) → 다중이동 되돌림
        host(page, "UNDO"); page.wait_for_timeout(150)
        check("UNDO 2 → 다중이동 복원(C1 A flow)", block_info(page, 0, 0)["position"] == c1a_pos)

        # UNDO 3 (키보드) → 텍스트 되돌림
        page.keyboard.press("Control+z"); page.wait_for_timeout(150)
        check("Ctrl+Z 3 → 텍스트 원문 복원", block_info(page, 0, 0)["text"] == t_orig)

        browser.close()
        print("\n=== 되돌리기 보편성(스펙 #6) ===")
        ok = True
        for name, passed in results:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            ok = ok and passed
        print(f"결과: {'ALL PASS' if ok else 'FAIL 있음'}")
        return ok


def test_paging():
    """3f: 편집 모드 한 장씩 페이징 — 진입/이동/클램프/직렬화 청결/보기복원."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, page = make_page(pw)  # make_page가 편집 모드 진입 → 페이징 ON
        results = []

        def check(name, cond, extra=""):
            results.append((name, bool(cond), extra))

        # 진입: 페이지 0, 카드1만 표시
        pg = wait_msg(page, "PAGE")
        check("진입 PAGE count=2·index=0", pg and pg.get("count") == 2 and pg.get("index") == 0)
        check("카드1 표시·카드2 숨김", (not card_hidden(page, 0)) and card_hidden(page, 1))

        # SET_PAGE 1 → 카드2만 표시
        clear_msgs(page)
        host(page, "SET_PAGE", index=1)
        pg = wait_msg(page, "PAGE")
        check("SET_PAGE 1 → PAGE index=1", pg and pg.get("index") == 1)
        check("카드2 표시·카드1 숨김", (not card_hidden(page, 1)) and card_hidden(page, 0))

        # 경계 클램프
        clear_msgs(page)
        host(page, "SET_PAGE", index=9)
        pg = wait_msg(page, "PAGE")
        check("경계 클램프 → index=1(마지막)", pg and pg.get("index") == 1)

        # 직렬화 청결: pi-hidden·아티팩트 흔적 0, 카드 2개 온전
        html = get_html(page)
        check("serialize: pi-hidden 잔재 0", "pi-hidden" not in html)
        check("serialize: data-pi 0·카드 2 유지", "data-pi-" not in html and html.count("data-screen-label") == 2)

        # 보기 모드 전환 → 전 카드 표시 복원
        host(page, "SET_MODE", mode="view")
        page.wait_for_timeout(120)
        check("보기 모드 → 전 카드 표시", (not card_hidden(page, 0)) and (not card_hidden(page, 1)))

        browser.close()
        print("\n=== 페이징(3f) ===")
        ok = True
        for name, passed, extra in results:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}" + (f"  ({extra})" if extra else ""))
            ok = ok and passed
        print(f"결과: {'ALL PASS' if ok else 'FAIL 있음'}")
        return ok


def test_insert_image():
    """INSERT_IMAGE(S0): activeCard 삽입 + 직렬화 생존(data-asset-id, data-pi 0) + undo/redo."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, page = make_page(pw)   # SET_MODE edit(=paged), activeCard=0
        results = []

        def check(name, cond):
            results.append((name, bool(cond)))

        # 카드2(index1)로 페이지 이동 후 삽입 → 카드2에만 들어가야 함(activeCard 한정)
        goto_card(page, 1)
        clear_msgs(page)
        host(page, "INSERT_IMAGE",
             url="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA=",
             assetId="A1", sourceType="upload-owned")
        page.wait_for_timeout(150)

        counts = page.evaluate("""() => {
          const cards = document.querySelectorAll('[data-screen-label]');
          return [cards[0].querySelectorAll('img').length, cards[1].querySelectorAll('img').length];
        }""")
        check("삽입: activeCard(카드2)에 img 1개", counts[1] == 1)
        check("삽입: 다른 카드(카드1)엔 0개", counts[0] == 0)

        sel = last(page, "SELECTED")
        check("삽입 후 img 선택", sel is not None and sel.get("tag") == "img")

        # 직렬화 생존
        html = get_html(page)
        check("serialize: data-asset-id 생존", 'data-asset-id="A1"' in html)
        check("serialize: data-source-type 생존", 'data-source-type="upload-owned"' in html)
        check("serialize: data-pi 아티팩트 0", "data-pi-" not in html)
        check("serialize: img 1개", html.count("<img") == 1)

        # undo → img 제거, redo → 복원
        host(page, "UNDO"); page.wait_for_timeout(120)
        after_undo = page.evaluate("() => document.querySelectorAll('img').length")
        check("undo→img 제거", after_undo == 0)
        host(page, "REDO"); page.wait_for_timeout(120)
        after_redo = page.evaluate("() => document.querySelectorAll('img').length")
        check("redo→img 복원", after_redo == 1)

        browser.close()
        print("\n=== INSERT_IMAGE (S0) ===")
        ok = True
        for name, passed in results:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            ok = ok and passed
        print(f"결과: {'ALL PASS' if ok else 'FAIL 있음'}")
        return ok


def test_highlight():
    """HIGHLIGHT(팩트 점프): 현재 카드 안 수치 위에 오버레이 마커.
    핵심 불변식 — DOM에 <mark> 삽입 없음 → 저장 HTML 무오염 + 자동저장(DIRTY) 미기동."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, page = make_page(pw)   # SET_MODE edit(=paged), activeCard=0
        results = []

        def check(name, cond):
            results.append((name, bool(cond)))

        def visible_marks():
            return page.evaluate(
                """() => Array.from(document.querySelectorAll('[data-pi-mark]'))
                  .filter(m => getComputedStyle(m).display !== 'none').length"""
            )

        # 카드 index 1(카드2)로 이동 후, 그 카드에 있는 텍스트("카드2 B")를 하이라이트
        goto_card(page, 1)
        clear_msgs(page)
        host(page, "HIGHLIGHT", value="카드2 B")
        hl = wait_msg(page, "HIGHLIGHTED")
        # 1) 마커가 실제로 보인다(display:block, 레이아웃 필요 — 실 Chromium이라 getClientRects 동작)
        check("HIGHLIGHT → HIGHLIGHTED found>=1", hl is not None and (hl.get("found") or 0) >= 1)
        check("HIGHLIGHT → 보이는 마커>=1개", visible_marks() >= 1)

        # 3) 자동저장 미기동: HIGHLIGHT 후 DIRTY 메시지가 오지 않아야 함(get_html 전에 검사 — get_html이 msgs를 비움)
        check("HIGHLIGHT → DIRTY 없음(자동저장 잠듦)", len(msgs(page, "DIRTY")) == 0)

        # 2) 저장 HTML 무오염: serialize가 data-pi-mark를 제거 → 원본 오염 없음
        html = get_html(page)
        check("serialize: data-pi-mark 0(저장 무오염)", "data-pi-mark" not in html)
        check("serialize: data-pi 아티팩트 0", "data-pi-" not in html)

        # 4) 다른 카드로 이동 → 이전 카드 마커 전부 숨김(clearHighlight)
        goto_card(page, 0)
        check("SET_PAGE 0 → 보이는 마커 0개", visible_marks() == 0)

        browser.close()
        print("\n=== 하이라이트(팩트 점프) ===")
        ok = True
        for name, passed in results:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            ok = ok and passed
        print(f"결과: {'ALL PASS' if ok else 'FAIL 있음'}")
        return ok


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    ok = True
    if mode in ("all", "baseline"):
        ok = test_baseline() and ok
    if mode in ("all", "multi"):
        ok = test_multiselect() and ok
    if mode in ("all", "align"):
        ok = test_align_numeric_textundo() and ok
    if mode in ("all", "undo"):
        ok = test_undo_universality() and ok
    if mode in ("all", "paging"):
        ok = test_paging() and ok
    if mode in ("all", "insert"):
        ok = test_insert_image() and ok
    if mode in ("all", "highlight"):
        ok = test_highlight() and ok
    sys.exit(0 if ok else 1)
