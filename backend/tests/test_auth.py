"""인증 테스트 — auth 우회 override 없이 실제 세션/보호 동작 검증."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import db as _db
from backend.core.config import settings
from backend.main import app


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "auth.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setattr(settings, "SESSION_TTL_HOURS", 72)
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "RENDER_TOKEN", "")
    await _db.migrate()
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Task 2: 스키마 ─────────────────────────────────────────────────────────

async def test_migrate_creates_auth_tables():
    import aiosqlite
    from backend.core.db import _db_path
    async with aiosqlite.connect(_db_path()) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cur:
            names = {row[0] for row in await cur.fetchall()}
    assert {"users", "sessions", "invites"} <= names


# ── Task 3: 해싱 ───────────────────────────────────────────────────────────

def test_hash_and_verify_password():
    from backend.core.auth import hash_password, verify_password
    h = hash_password("correct horse")
    assert h != "correct horse"          # 평문 저장 금지
    assert verify_password(h, "correct horse") is True
    assert verify_password(h, "wrong") is False


# ── Task 4: DB 헬퍼 ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_db_helpers():
    from backend.core import db
    uid = await db.create_user("a@b.com", "hash1")
    assert isinstance(uid, int)
    by_email = await db.get_user_by_email("a@b.com")
    assert by_email["id"] == uid and by_email["password_hash"] == "hash1"
    by_id = await db.get_user_by_id(uid)
    assert by_id["email"] == "a@b.com"
    assert await db.get_user_by_email("missing@x.com") is None


@pytest.mark.asyncio
async def test_session_db_helpers():
    from backend.core import db
    uid = await db.create_user("s@b.com", "h")
    await db.create_session("tok-123", uid, ttl_hours=72)
    sess = await db.get_valid_session("tok-123")
    assert sess["user_id"] == uid
    await db.delete_session("tok-123")
    assert await db.get_valid_session("tok-123") is None


@pytest.mark.asyncio
async def test_expired_session_not_returned():
    from backend.core import db
    uid = await db.create_user("e@b.com", "h")
    await db.create_session("tok-exp", uid, ttl_hours=-1)  # 이미 만료
    assert await db.get_valid_session("tok-exp") is None


@pytest.mark.asyncio
async def test_invite_consume_once():
    from backend.core import db
    await db.create_invite("INV1")
    assert (await db.get_invite("INV1"))["used_by"] is None
    uid = await db.create_user("i@b.com", "h")
    assert await db.consume_invite("INV1", uid) is True
    assert await db.consume_invite("INV1", uid) is False  # 재사용 불가
    assert (await db.get_invite("INV1"))["used_by"] == uid


# ── Task 5: get_current_user ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_current_user_with_valid_session():
    from starlette.requests import Request
    from backend.core import db
    from backend.core.auth import get_current_user
    uid = await db.create_user("c@b.com", "h")
    await db.create_session("sess-ok", uid, ttl_hours=72)
    scope = {"type": "http", "headers": [(b"cookie", b"session=sess-ok")]}
    user = await get_current_user(Request(scope))
    assert user["email"] == "c@b.com"


@pytest.mark.asyncio
async def test_get_current_user_no_cookie_raises_401():
    from fastapi import HTTPException
    from starlette.requests import Request
    from backend.core.auth import get_current_user
    scope = {"type": "http", "headers": []}
    with pytest.raises(HTTPException) as exc:
        await get_current_user(Request(scope))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_render_token_bypass(monkeypatch):
    from starlette.requests import Request
    from backend.core.config import settings
    from backend.core.auth import get_current_user
    monkeypatch.setattr(settings, "RENDER_TOKEN", "rt-secret")
    scope = {"type": "http", "headers": [(b"x-render-token", b"rt-secret")]}
    user = await get_current_user(Request(scope))
    assert user["role"] == "service"


# ── Task 6: auth 라우터 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signup_requires_valid_invite(client):
    resp = await client.post("/api/auth/signup", json={
        "email": "new@b.com", "password": "password1", "invite": "BAD"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ERR-AUTH-004"


@pytest.mark.asyncio
async def test_signup_with_invite_sets_cookie(client):
    from backend.core import db
    await db.create_invite("GOODCODE")
    resp = await client.post("/api/auth/signup", json={
        "email": "new@b.com", "password": "password1", "invite": "GOODCODE"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "new@b.com"
    assert "session" in resp.cookies


@pytest.mark.asyncio
async def test_signup_duplicate_email(client):
    from backend.core import db
    await db.create_invite("C1")
    await db.create_invite("C2")
    await client.post("/api/auth/signup", json={
        "email": "dup@b.com", "password": "password1", "invite": "C1"})
    resp = await client.post("/api/auth/signup", json={
        "email": "dup@b.com", "password": "password1", "invite": "C2"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "ERR-AUTH-003"


@pytest.mark.asyncio
async def test_login_success_and_me(client):
    from backend.core import db
    from backend.core.auth import hash_password
    await db.create_user("doc@b.com", hash_password("password1"))
    login = await client.post("/api/auth/login", json={
        "email": "doc@b.com", "password": "password1"})
    assert login.status_code == 200
    assert "session" in login.cookies
    me = await client.get("/api/auth/me")  # AsyncClient가 쿠키 유지
    assert me.status_code == 200
    assert me.json()["email"] == "doc@b.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    from backend.core import db
    from backend.core.auth import hash_password
    await db.create_user("doc2@b.com", hash_password("password1"))
    resp = await client.post("/api/auth/login", json={
        "email": "doc2@b.com", "password": "WRONG"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "ERR-AUTH-005"


@pytest.mark.asyncio
async def test_me_without_login_401(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_session(client):
    from backend.core import db
    from backend.core.auth import hash_password
    await db.create_user("lo@b.com", hash_password("password1"))
    await client.post("/api/auth/login", json={"email": "lo@b.com", "password": "password1"})
    assert (await client.get("/api/auth/me")).status_code == 200
    await client.post("/api/auth/logout")
    assert (await client.get("/api/auth/me")).status_code == 401


# ── Task 7: 라우터 보호 + 렌더 토큰 우회 ──────────────────────────────────

@pytest.mark.asyncio
async def test_projects_requires_auth(client):
    resp = await client.get("/api/projects")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_render_token_bypasses_protected_route(client, monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "RENDER_TOKEN", "rt-secret")
    resp = await client.get("/api/projects", headers={"X-Render-Token": "rt-secret"})
    assert resp.status_code == 200
