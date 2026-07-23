import json

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.agents.deck import ig_publish
from backend.core import config, crypto, db
from backend.main import app
from backend.tests.conftest import login_cookie


@pytest_asyncio.fixture
async def _ctx(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path / 't.db'}")
    monkeypatch.setattr(config.settings, "SOCIAL_TOKEN_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(config.settings, "PUBLIC_CARD_URL_SECRET", "test-secret-0123456789")
    monkeypatch.setattr(config.settings, "PUBLIC_BASE_URL", "https://app.test")
    monkeypatch.setattr(config.settings, "PUBLISH_CREDIT_COST", 5)
    await db.migrate()


async def test_publish_happy_path(_ctx, monkeypatch):
    uid = await db.create_user("p@x.io", "")
    await db.create_job("jP", "p.pdf", user_id=uid)   # R2: jobs 행 (require_owned_job용)
    await db.save_authored_deck(
        "jP", '<div data-screen-label="01"></div><div data-screen-label="02"></div>', "[]", 2, "paper")
    # 캡션 캐시 시드 → _deck_caption_text가 generate_caption(실 Sonnet) 미호출 (비용 0)
    await db.set_deck_caption("jP", json.dumps({"caption": "테스트 캡션", "hashtags": ["#논문"]}))
    await db.upsert_social_account(uid, "instagram", "ig9", "shop", crypto.encrypt("TOK"), None)
    await db.add_credits(uid, 10)

    captured = {}

    async def fake_pub(ig_user_id, token, urls, caption):
        captured["urls"] = urls
        captured["token"] = token
        return "https://instagram.com/p/OK"
    monkeypatch.setattr(ig_publish, "publish_carousel", fake_pub)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        c.cookies.update(await login_cookie(uid))
        r = await c.post("/api/deck/jP/publish/instagram")
    assert r.status_code == 200
    assert r.json()["permalink"] == "https://instagram.com/p/OK"
    assert captured["token"] == "TOK"                     # 복호화 토큰 전달
    assert captured["urls"][0].startswith("https://app.test/api/deck/jP/cards/1/public?exp=")
    assert len(captured["urls"]) == 2                     # 카드 2장
    assert await db.get_credits(uid) == 5                 # 10 - 5 차감


async def test_publish_blocks_without_connection(_ctx):
    uid = await db.create_user("p2@x.io", "")
    await db.create_job("jN", "p.pdf", user_id=uid)
    await db.save_authored_deck("jN", "<div data-screen-label='01'></div>", "[]", 1, "p")
    await db.add_credits(uid, 10)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        c.cookies.update(await login_cookie(uid))
        r = await c.post("/api/deck/jN/publish/instagram")
    assert r.status_code == 400   # 미연동


async def test_publish_blocks_insufficient_credits(_ctx):
    uid = await db.create_user("p3@x.io", "")
    await db.create_job("jC", "p.pdf", user_id=uid)
    await db.save_authored_deck("jC", "<div data-screen-label='01'></div>", "[]", 1, "p")
    await db.set_deck_caption("jC", json.dumps({"caption": "c", "hashtags": []}))
    await db.upsert_social_account(uid, "instagram", "ig9", "shop", crypto.encrypt("TOK"), None)
    await db.add_credits(uid, 2)   # < 5
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        c.cookies.update(await login_cookie(uid))
        r = await c.post("/api/deck/jC/publish/instagram")
    assert r.status_code == 402
    assert await db.get_credits(uid) == 2   # 미차감
