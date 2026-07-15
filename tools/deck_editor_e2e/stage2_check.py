"""Stage 2 실 브라우저 E2E — 실제 Next DeckEditor iframe에서 3e 동작 확인.

세션 쿠키 주입 → /deck/<id> → 편집모드 → 실 iframe agent ready →
shift클릭 다중선택(패널 '다중 2' 표시) → 정렬 → 저장 → PATCH 200 → '저장됨'.

전제: uvicorn(8000)·next dev(3000) 기동 중. 인자: <session_token>
"""
import os
import sys
import uuid
import asyncio

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = os.path.join(REPO, "backend", "polyinsight.db")
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, REPO)
import deck_harness as H  # noqa: E402

TOKEN = sys.argv[1]


async def seed_deck():
    from backend.core import db
    await db.migrate()
    job_id = "s2-" + uuid.uuid4().hex[:8]
    await db.create_job(job_id, title="3e stage2")
    await db.update_job_status(job_id, "DONE")
    await db.save_authored_deck(
        job_id, H.build_deck(),
        '{"verified":0,"unverified":0,"claims":[]}',
        2, paper_text=None,
    )
    return job_id


def run():
    from playwright.sync_api import sync_playwright
    job_id = asyncio.run(seed_deck())
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond), extra))

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1400, "height": 1000})
        ctx.add_cookies([{"name": "session", "value": TOKEN, "domain": "localhost", "path": "/"}])
        page = ctx.new_page()
        page.goto(f"http://localhost:3000/deck/{job_id}", wait_until="commit")

        # 편집 버튼 등장(덱 로드 완료) → 클릭
        page.get_by_role("button", name="편집", exact=True).wait_for(timeout=20000)
        check("덱 로드(편집 버튼)", True)
        page.get_by_role("button", name="편집", exact=True).click()

        # 실 iframe agent ready
        page.wait_for_selector('iframe[title="deck-editor"]', timeout=10000)
        frame_el = page.query_selector('iframe[title="deck-editor"]')
        frame = frame_el.content_frame()
        frame.wait_for_function("() => window.__piAgent === true", timeout=10000)
        check("실 iframe agent 주입·ready", True)

        # 카드1 블록A 클릭 → 블록B shift클릭 → 패널 '다중' 표시
        frame.get_by_text("카드1 블록A").click()
        frame.get_by_text("카드1 블록B").click(modifiers=["Shift"])
        try:
            page.wait_for_selector("text=다중", timeout=5000)
            check("다중선택 → 패널 '다중 N' 표시", True)
        except Exception:
            check("다중선택 → 패널 '다중 N' 표시", False, "패널에 '다중' 미표시")

        # 정렬(왼쪽) 버튼 → dirty → 저장 활성
        page.get_by_title("왼쪽 정렬").click()

        # 저장 → PATCH 200
        try:
            with page.expect_response(
                lambda r: "/api/deck/" in r.url and r.request.method == "PATCH", timeout=30000
            ) as ri:
                page.get_by_role("button", name="저장", exact=True).click()
            resp = ri.value
            check("저장 → PATCH 200", resp.status == 200, f"status={resp.status}")
        except Exception as e:
            check("저장 → PATCH 200", False, str(e)[:80])

        # UI '저장됨' 복귀
        try:
            page.get_by_role("button", name="저장됨", exact=True).wait_for(timeout=15000)
            check("저장 후 UI '저장됨'", True)
        except Exception:
            check("저장 후 UI '저장됨'", False)

        browser.close()

    print("\n=== Stage 2 실 브라우저 E2E ===")
    ok = True
    for name, passed, extra in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}" + (f"  ({extra})" if extra else ""))
        ok = ok and passed
    print(f"job_id={job_id}")
    print(f"결과: {'ALL PASS' if ok else 'FAIL 있음'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
