import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import config, crypto, db, oauth
from backend.main import app
from backend.tests.conftest import login_cookie


@pytest_asyncio.fixture
async def _client(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path / 't.db'}")
    monkeypatch.setattr(config.settings, "SOCIAL_TOKEN_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_ID", "cid")
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_SECRET", "sec")
    await db.migrate()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


async def test_callback_stores_encrypted_token(_client, monkeypatch):
    uid = await db.create_user("i@x.io", "")
    _client.cookies.update(await login_cookie(uid))

    async def fake_exchange(code):
        return {"ig_user_id": "ig9", "access_token": "LONGTOK",
                "expires_in": 5184000, "ig_username": "shop"}
    monkeypatch.setattr(oauth, "instagram_exchange", fake_exchange)

    r = await _client.get("/api/auth/oauth/instagram/start", follow_redirects=False)
    assert r.status_code == 302
    state = _client.cookies.get("oauth_state")
    assert state

    r2 = await _client.get(
        f"/api/auth/oauth/instagram/callback?code=C&state={state}", follow_redirects=False)
    assert r2.status_code == 302

    acct = await db.get_social_account(uid, "instagram")
    assert acct is not None
    assert acct["ig_user_id"] == "ig9"
    assert acct["access_token"] != "LONGTOK"           # 암호화 저장
    assert crypto.decrypt(acct["access_token"]) == "LONGTOK"


async def test_callback_rejects_bad_state(_client):
    uid = await db.create_user("i2@x.io", "")
    _client.cookies.update(await login_cookie(uid))
    # state 쿠키 없이 콜백 → CSRF 거부 리다이렉트, 저장 안 됨
    r = await _client.get(
        "/api/auth/oauth/instagram/callback?code=C&state=forged", follow_redirects=False)
    assert r.status_code == 302
    assert await db.get_social_account(uid, "instagram") is None
