import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import db
from backend.main import app
from backend.tests.conftest import login_cookie


@pytest_asyncio.fixture
async def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path / 't.db'}")
    await db.migrate()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


async def test_status_not_connected(_client):
    uid = await db.create_user("s@x.io", "")
    _client.cookies.update(await login_cookie(uid))
    r = await _client.get("/api/social/instagram/status")
    assert r.status_code == 200
    assert r.json() == {"connected": False, "username": None}


async def test_status_connected_then_disconnect(_client):
    uid = await db.create_user("s2@x.io", "")
    _client.cookies.update(await login_cookie(uid))
    await db.upsert_social_account(uid, "instagram", "ig9", "shop", "ENC", None)

    r = await _client.get("/api/social/instagram/status")
    assert r.json() == {"connected": True, "username": "shop"}

    r2 = await _client.delete("/api/social/instagram")
    assert r2.status_code == 200

    r3 = await _client.get("/api/social/instagram/status")
    assert r3.json()["connected"] is False
