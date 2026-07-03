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
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    from backend.core import ratelimit
    ratelimit.reset_all()
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
async def test_signup_open_no_invite_sets_cookie(client):
    """오픈 가입(2026-07-02 초대코드 폐기) — invite 없이 가입 성공 + 세션 발급."""
    resp = await client.post("/api/auth/signup", json={
        "email": "new@b.com", "password": "Str0ngPass!22"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "new@b.com"
    assert "session" in resp.cookies


@pytest.mark.asyncio
async def test_signup_short_password_rejected(client):
    resp = await client.post("/api/auth/signup", json={
        "email": "short@b.com", "password": "short"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "ERR-AUTH-002"


@pytest.mark.asyncio
async def test_signup_duplicate_email(client):
    await client.post("/api/auth/signup", json={
        "email": "dup@b.com", "password": "Str0ngPass!22"})
    resp = await client.post("/api/auth/signup", json={
        "email": "dup@b.com", "password": "Str0ngPass!22"})
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


# ── 유저별 격리 + IDOR (2026-07-02) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_lists_only_own_jobs(client):
    from backend.core import db
    from backend.core.auth import hash_password
    a = await db.create_user("a@own.test", hash_password("password1"))
    b = await db.create_user("b@own.test", hash_password("password1"))
    await db.create_job("job-a", "a.pdf", user_id=a)
    await db.create_job("job-b", "b.pdf", user_id=b)
    await client.post("/api/auth/login", json={"email": "a@own.test", "password": "password1"})
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    ids = [p["jobId"] for p in resp.json()["projects"]]
    assert ids == ["job-a"]  # B의 잡 안 보임


@pytest.mark.asyncio
async def test_cannot_access_others_job_404(client):
    """IDOR — 남의 job_id 알아도 접근 불가(404, 존재 은닉)."""
    from backend.core import db
    from backend.core.auth import hash_password
    await db.create_user("a2@own.test", hash_password("password1"))
    b = await db.create_user("b2@own.test", hash_password("password1"))
    await db.create_job("job-b2", "b.pdf", user_id=b)
    await client.post("/api/auth/login", json={"email": "a2@own.test", "password": "password1"})
    assert (await client.get("/api/status/job-b2")).status_code == 404
    assert (await client.get("/api/cards/job-b2")).status_code == 404


# ── 이메일 인증 (2026-07-02) ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signup_sets_unverified_and_me(client):
    resp = await client.post("/api/auth/signup", json={"email": "unv@x.com", "password": "Str0ngPass!22"})
    assert resp.status_code == 200
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["emailVerified"] is False


@pytest.mark.asyncio
async def test_email_verify_confirm_flow(client):
    import hashlib
    from backend.core import db
    from backend.core.auth import hash_password
    uid = await db.create_user("ev@x.com", hash_password("password1"))
    raw = "rawtoken-abc"
    th = hashlib.sha256(raw.encode()).hexdigest()
    await db.create_auth_token(th, uid, "verify_email", 24)
    r = await client.post("/api/auth/confirm-verify", json={"token": raw})
    assert r.status_code == 200
    assert (await db.get_user_by_id(uid))["email_verified"] == 1
    # 단일사용 — 재사용 400
    r2 = await client.post("/api/auth/confirm-verify", json={"token": raw})
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_email_verify_invalid_token(client):
    r = await client.post("/api/auth/confirm-verify", json={"token": "nope-not-a-token"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "ERR-AUTH-006"


# ── 비밀번호 재설정 (2026-07-03) ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password_symmetric_response(client):
    """존재/부재 이메일 모두 동일 200 {"ok": true} — 열거 대칭."""
    from backend.core import db
    from backend.core.auth import hash_password
    await db.create_user("exists@x.com", hash_password("password!!9"))
    r1 = await client.post("/api/auth/forgot-password", json={"email": "exists@x.com"})
    r2 = await client.post("/api/auth/forgot-password", json={"email": "absent@x.com"})
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json() == {"ok": True}


@pytest.mark.asyncio
async def test_reset_password_full_flow_invalidates_sessions(client):
    """재설정 성공 → 새 비번 로그인 OK, 구 비번 401, 기존 세션 무효화, 타 유저 세션 생존."""
    import hashlib
    from backend.core import db
    from backend.core.auth import hash_password

    uid = await db.create_user("victim@x.com", hash_password("oldpass!!9"))
    other = await db.create_user("other@x.com", hash_password("otherpass9"))
    await db.create_session("victim-tok", uid, 72)
    await db.create_session("other-tok", other, 72)

    raw = "reset-raw-token"
    th = hashlib.sha256(raw.encode()).hexdigest()
    await db.create_auth_token(th, uid, "reset_password", 2)

    r = await client.post("/api/auth/reset-password", json={"token": raw, "password": "newpass!!10"})
    assert r.status_code == 200

    assert await db.get_valid_session("victim-tok") is None   # 전 세션 무효화
    assert await db.get_valid_session("other-tok") is not None  # 타 유저 생존

    ok = await client.post("/api/auth/login", json={"email": "victim@x.com", "password": "newpass!!10"})
    assert ok.status_code == 200
    bad = await client.post("/api/auth/login", json={"email": "victim@x.com", "password": "oldpass!!9"})
    assert bad.status_code == 401

    # 토큰 단일사용 — 재사용 400
    again = await client.post("/api/auth/reset-password", json={"token": raw, "password": "anotherpw11"})
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_rejects_weak_or_bad_token(client):
    r = await client.post("/api/auth/reset-password", json={"token": "x", "password": "short"})
    assert r.status_code == 400  # 길이
    r = await client.post("/api/auth/reset-password", json={"token": "x", "password": "password123"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "ERR-AUTH-007"  # 흔한 비번
    r = await client.post("/api/auth/reset-password", json={"token": "invalid", "password": "goodpass!!9"})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "ERR-AUTH-006"  # 무효 토큰


@pytest.mark.asyncio
async def test_forgot_password_skips_oauth_only_user(client, monkeypatch):
    """OAuth 전용 유저(빈 해시)는 재설정 메일 발송 안 함 — 응답은 동일."""
    from backend.core import db, email as email_mod
    sent = []
    async def fake_send(to, link):
        sent.append(to)
        return True
    monkeypatch.setattr(email_mod, "send_reset_email", fake_send)
    await db.create_user("social@x.com", "")  # OAuth 전용
    r = await client.post("/api/auth/forgot-password", json={"email": "social@x.com"})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert sent == []


@pytest.mark.asyncio
async def test_reset_password_invalidates_sibling_tokens(client):
    """재설정 성공 시 같은 유저의 다른 미사용 재설정 토큰도 무효화 — 재탈취 차단."""
    import hashlib
    from backend.core import db
    from backend.core.auth import hash_password
    uid = await db.create_user("sib@x.com", hash_password("oldpass!!9"))
    raws = ["sib-token-1", "sib-token-2"]
    for raw in raws:
        await db.create_auth_token(hashlib.sha256(raw.encode()).hexdigest(), uid, "reset_password", 2)

    r = await client.post("/api/auth/reset-password", json={"token": raws[0], "password": "newpass!!10"})
    assert r.status_code == 200
    # 형제 토큰으로 재시도 → 400 (무효화됨)
    r2 = await client.post("/api/auth/reset-password", json={"token": raws[1], "password": "hijack!!11"})
    assert r2.status_code == 400
