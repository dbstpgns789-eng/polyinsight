"""Stage 1 풀스택 저장경로 검증 (유료 파이프라인 없이).

흐름: 하네스로 실제 3e 편집(다중선택+정렬) HTML 생성 → 합성 덱을 DB 직접삽입 →
실 백엔드 PATCH /api/deck/{id}(X-Render-Token 우회) → 재검증+PNG 재렌더 200 확인 →
카드 PNG 수신 확인 → 저장 HTML 청결(data-pi 잔재 0, 정렬 반영) 확인.

전제: uvicorn이 아래 DB로 RENDER_TOKEN=testtoken 기동 중.
"""
import os
import sys
import json
import uuid
import asyncio

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(REPO, "backend", "polyinsight.db")
os.environ["DATABASE_URL"] = DB  # backend.core.config 임포트 전에 지정
TOKEN = "testtoken"

sys.path.insert(0, os.path.dirname(__file__))
import deck_harness as H  # noqa: E402


def gen_edited_html():
    """실제 3e 편집(카드2 정렬 왼쪽 + 카드1 A 이동)을 가한 뒤 agent serialize 결과."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser, page = H.make_page(pw)
        # 카드1 블록A 드래그 이동(단일)
        a = H.block_info(page, 0, 0)
        H.drag(page, a["vx"] + 30, a["vy"] + 30, a["vx"] + 140, a["vy"] + 100)
        H.wait_msg(page, "HISTORY_STATE")
        # 카드2 전체 선택 → 왼쪽 정렬
        ax, ay = H.center(page, 1, 0)
        page.mouse.click(ax, ay); H.wait_msg(page, "SELECTED")
        for bi in (1, 2):
            sx, sy = H.center(page, 1, bi); H.shift_click(page, sx, sy)
        page.wait_for_timeout(120)
        H.host(page, "ALIGN", axis="left"); H.wait_msg(page, "HISTORY_STATE")
        html = H.get_html(page)
        browser.close()
    return html


async def seed(job_id, html):
    sys.path.insert(0, REPO)
    from backend.core import db
    await db.migrate()
    await db.create_job(job_id, title="3e fullstack test")
    await db.save_authored_deck(
        job_id, html,
        json.dumps({"verified": 0, "unverified": 0, "claims": []}),
        html.count("data-screen-label"), paper_text=None,
    )


def http(method, path, body=None, token=True):
    import urllib.request
    import urllib.error
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Render-Token"] = TOKEN
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://localhost:8000{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.read(), r.headers.get_content_type()
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get_content_type()


def main():
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond), extra))

    original = H.build_deck()
    edited = gen_edited_html()
    check("편집 HTML 생성(정렬/이동 반영)", "left: 100px" in edited or "left:100px" in edited, "카드2 정렬")
    check("편집 HTML 아티팩트 0", "data-pi-" not in edited and "contenteditable" not in edited)

    job_id = "e2e-" + uuid.uuid4().hex[:8]
    asyncio.run(seed(job_id, original))

    # PATCH: 편집 HTML 저장 → 재검증 + PNG 재렌더
    status, raw, _ = http("PATCH", f"/api/deck/{job_id}", {"html": edited})
    ok200 = status == 200
    check("PATCH 200", ok200, f"status={status} {raw[:160] if not ok200 else ''}")
    if ok200:
        res = json.loads(raw)
        check("응답 cardCount==2", res.get("cardCount") == 2, f"cardCount={res.get('cardCount')}")
        check("응답 verify 존재", "verify" in res)

    # 카드 PNG 재렌더 확인
    s1, png, ctype = http("GET", f"/api/deck/{job_id}/cards/1")
    check("카드1 PNG 수신", s1 == 200 and ctype == "image/png" and len(png) > 500, f"status={s1} type={ctype} bytes={len(png)}")

    # 저장 HTML 청결 + 정렬 반영
    sg, graw, _ = http("GET", f"/api/deck/{job_id}")
    if sg == 200:
        saved = json.loads(graw)
        shtml = saved.get("html") or ""
        check("저장 HTML data-pi 잔재 0", "data-pi-" not in shtml)
        check("저장 HTML data-screen-label 2개", shtml.count("data-screen-label") == 2)
        check("저장 HTML 정렬 반영(left:100px 3회)", shtml.count("left: 100px") + shtml.count("left:100px") >= 3)
    else:
        check("GET deck 200", False, f"status={sg}")

    print("\n=== Stage 1 풀스택 저장경로 ===")
    ok = True
    for name, passed, extra in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}" + (f"  ({extra})" if extra else ""))
        ok = ok and passed
    print(f"job_id={job_id}")
    print(f"결과: {'ALL PASS' if ok else 'FAIL 있음'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
