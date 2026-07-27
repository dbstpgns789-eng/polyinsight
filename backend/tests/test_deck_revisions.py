# -*- coding: utf-8 -*-
"""덱 판 보관(revision) — 2026-07-26.

지금 authored_deck는 job_id PK UPSERT라 저장할 때마다 이전 판이 소실된다.
되돌리기는 iframe undo 스택과 프론트 useState 배열뿐이라 새로고침하면 둘 다 죽는다.
=> 서버에 복구 지점을 남긴다. 단 자동저장(3초 유휴 디바운스)은 판을 만들지 않는다 —
   판이 수백 개가 되면 목록이 사람이 읽을 수 없는 것이 된다.
"""
import pytest
import pytest_asyncio

from backend.core import db as _db
from backend.core.config import settings

DECK = '<!DOCTYPE html><html><body><div data-screen-label="01">카드</div></body></html>'


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blob"))
    await _db.migrate()
    yield


@pytest.mark.asyncio
async def test_saved_revision_is_listed_and_retrievable():
    """적재한 판이 목록에 뜨고, 단건 조회로 HTML을 되찾을 수 있다."""
    await _db.create_job("j1", "p.pdf", user_id=1)

    rev_id = await _db.save_deck_revision("j1", DECK, "[]", 1, source="author")

    rows = await _db.list_deck_revisions("j1")
    assert len(rows) == 1
    assert rows[0]["id"] == rev_id
    assert rows[0]["source"] == "author"
    assert rows[0]["card_count"] == 1
    assert "html" not in rows[0], "목록에 HTML 전문을 실으면 안 된다(덱당 수십 KB)"

    got = await _db.get_deck_revision("j1", rev_id)
    assert got["html"] == DECK


@pytest_asyncio.fixture
async def no_render(monkeypatch):
    """PNG 재렌더(Playwright)는 이 테스트의 관심사가 아니다."""
    from backend.agents.deck import pipeline as _pipe

    async def _fake(html, job_id=None, **kw):
        return [], []
    monkeypatch.setattr(_pipe, "render_deck", _fake)


EDITED = DECK.replace("카드", "고친 카드")


@pytest.mark.asyncio
async def test_autosave_does_not_create_revision(no_render):
    """자동저장(3초 유휴)은 판을 남기지 않는다 — 남기면 목록이 수백 개가 된다."""
    from backend.agents.deck.pipeline import persist_edited_deck

    await _db.create_job("j1", "p.pdf", user_id=1)
    await _db.save_authored_deck("j1", DECK, "[]", 1, paper_text="원문")

    await persist_edited_deck("j1", EDITED)

    assert await _db.list_deck_revisions("j1") == []
    assert (await _db.get_authored_deck("j1"))["html"] == EDITED, "덱 자체는 갱신돼야 한다"


@pytest.mark.asyncio
async def test_meaningful_save_creates_revision(no_render):
    """수동 저장·AI 편집처럼 의미 있는 경계는 되돌아갈 판을 남긴다."""
    from backend.agents.deck.pipeline import persist_edited_deck

    await _db.create_job("j1", "p.pdf", user_id=1)
    await _db.save_authored_deck("j1", DECK, "[]", 1, paper_text="원문")

    await persist_edited_deck("j1", EDITED, revision_source="manual")

    rows = await _db.list_deck_revisions("j1")
    assert len(rows) == 1
    assert rows[0]["source"] == "manual"
    assert (await _db.get_deck_revision("j1", rows[0]["id"]))["html"] == EDITED


@pytest.mark.asyncio
async def test_authoring_keeps_the_original(no_render, monkeypatch):
    """저작이 끝나면 모델이 처음 뱉은 판이 남는다.

    이게 없으면 첫 편집이 저장되는 순간 원본이 영영 사라진다.
    사용자가 만지다 망친 뒤 "처음 게 나았는데"라고 해도 돌아갈 데가 없다.
    """
    from backend.agents.deck import pipeline as _pipe
    from backend.agents.s1_extractor import s1_agent
    from backend.core.models import PaperMetadata, S1Output

    monkeypatch.setattr(settings, "DEV_MOCK_LLM", True)

    async def _fake_s1(inp):
        # word_count<100은 스캔본으로 보고 S1이 중단시킨다 — 500으로 통과시킨다.
        return S1Output(raw_text="원문 " * 500, page_map={1: "원문"}, word_count=500,
                        metadata=PaperMetadata(title="t", authors=["a"], year=2026, doi=None))

    monkeypatch.setattr(s1_agent, "execute", _fake_s1)

    await _db.create_job("j2", "p.pdf", user_id=1)
    await _pipe.run_authoring_pipeline("j2", b"%PDF-fake", card_count=7)

    rows = await _db.list_deck_revisions("j2")
    assert [r["source"] for r in rows] == ["author"]
    saved = (await _db.get_authored_deck("j2"))["html"]
    assert (await _db.get_deck_revision("j2", rows[0]["id"]))["html"] == saved


# ── API ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(no_render):
    from httpx import ASGITransport, AsyncClient

    from backend.main import app
    from backend.tests.conftest import login_cookie

    uid = await _db.create_user("r@x.io", "")
    await _db.create_job("jR", "p.pdf", user_id=uid)
    await _db.save_authored_deck("jR", DECK, "[]", 1, paper_text="원문")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        c.cookies.update(await login_cookie(uid))
        yield c


@pytest.mark.asyncio
async def test_autosave_patch_leaves_no_revision(client):
    """PATCH auto=true(자동저장)는 덱만 갱신하고 판을 남기지 않는다."""
    r = await client.patch("/api/deck/jR", json={"html": EDITED, "auto": True})
    assert r.status_code == 200

    assert await _db.list_deck_revisions("jR") == []
    assert (await _db.get_authored_deck("jR"))["html"] == EDITED


@pytest.mark.asyncio
async def test_manual_patch_is_listed_without_html(client):
    """수동 저장은 판을 남기고, 목록은 HTML 전문을 싣지 않는다."""
    await client.patch("/api/deck/jR", json={"html": EDITED})

    r = await client.get("/api/deck/jR/revisions")
    assert r.status_code == 200
    revs = r.json()["revisions"]
    assert len(revs) == 1
    assert revs[0]["source"] == "manual"
    assert revs[0]["cardCount"] == 1
    assert "html" not in revs[0]


@pytest.mark.asyncio
async def test_restore_brings_the_old_deck_back(client):
    """복원은 그 판으로 덱을 되돌리고, 복원 그 자체도 판으로 남는다."""
    await client.patch("/api/deck/jR", json={"html": EDITED})       # 판 1 = EDITED
    old_id = (await _db.list_deck_revisions("jR"))[0]["id"]
    await client.patch("/api/deck/jR", json={"html": DECK})          # 판 2 = DECK

    r = await client.post(f"/api/deck/jR/revisions/{old_id}/restore")
    assert r.status_code == 200
    assert r.json()["html"] == EDITED

    assert (await _db.get_authored_deck("jR"))["html"] == EDITED
    assert [x["source"] for x in await _db.list_deck_revisions("jR")] == \
        ["restore", "manual", "manual"], "되돌리기를 되돌릴 수 있어야 한다"


@pytest.mark.asyncio
async def test_ai_edit_creates_revision(client, monkeypatch):
    """AI 편집은 되돌릴 가능성이 가장 높은 경계다 — 반드시 판을 남긴다."""
    from backend.routers import deck as _router

    # 편집스펙 코어(2026-07-26) 이후 apply_nl_patch는 (html, applied, summary)를 준다.
    async def _fake_patch(html, instruction, paper_text=None, **kw):
        return EDITED, 1, "고쳤어요"
    monkeypatch.setattr(_router, "apply_nl_patch", _fake_patch)
    monkeypatch.setattr(_router.plans, "require_can_ai_designer", lambda u: None)
    monkeypatch.setattr(_router.plans, "author_charges_credits", lambda u: False)

    r = await client.post("/api/deck/jR/nlpatch", json={"instruction": "제목 키워"})
    assert r.status_code == 200

    revs = await _db.list_deck_revisions("jR")
    assert [x["source"] for x in revs] == ["ai_edit"]


@pytest.mark.asyncio
async def test_restore_rejects_other_jobs_revision(client):
    """남의 잡의 판은 복원할 수 없다(IDOR)."""
    await _db.create_job("jOther", "p.pdf", user_id=1)
    alien = await _db.save_deck_revision("jOther", DECK, "[]", 1, source="manual")

    r = await client.post(f"/api/deck/jR/revisions/{alien}/restore")
    assert r.status_code == 404
