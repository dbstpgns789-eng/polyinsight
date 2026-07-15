"""소셜 로그인(Google OAuth) — happy/sad path. 외부 핸드셰이크는 google_exchange 목킹."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import db as _db
from backend.core import oauth as oauth_core
from backend.core import ratelimit
from backend.core.config import settings
from backend.main import app


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'oauth.db'}")
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "RENDER_TOKEN", "")
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(settings, "WEB_BASE_URL", "http://localhost:3000")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "")
    monkeypatch.setattr(settings, "OAUTH_REDIRECT_BASE", "")
    # 헤르메틱: 기본은 크레딧 없음(dormant). enabled 테스트가 개별로 override.
    # (실 .env에 Google 크레딧이 있으면 dormant 테스트가 깨지던 것 수정)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "")
    ratelimit.reset_all()
    await _db.migrate()
    yield


@pytest_asyncio.fixture
async def client():
    # follow_redirects=False → 302를 그대로 검사
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           follow_redirects=False) as c:
        yield c


def _fake_exchange(sub="g-1", email="guser@x.com", verified=True):
    async def _f(code):
        return {"sub": sub, "email": email, "email_verified": verified, "name": "G User"}
    return _f


# ── start ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_dormant_when_no_credentials(client):
    """크리덴셜 없으면 구글로 안 가고 /login 복귀(앱 안 깨짐)."""
    r = await client.get("/api/auth/oauth/google/start")
    assert r.status_code == 302
    assert "/login?error=oauth_disabled" in r.headers["location"]


@pytest.mark.asyncio
async def test_start_redirects_to_google_with_state(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-cid")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-secret")
    r = await client.get("/api/auth/oauth/google/start")
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "client_id=test-cid" in loc
    assert "state=" in loc
    assert "localhost%3A3000%2Fapi%2Fauth%2Foauth%2Fgoogle%2Fcallback" in loc  # redirect_uri(프론트 오리진)
    assert "oauth_state" in r.cookies  # CSRF state 쿠키 발급


# ── callback happy ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_callback_creates_new_user_and_session(client, monkeypatch):
    monkeypatch.setattr(oauth_core, "google_exchange", _fake_exchange(email="new@x.com"))
    r = await client.get("/api/auth/oauth/google/callback",
                         params={"code": "c", "state": "S"}, cookies={"oauth_state": "S"})
    assert r.status_code == 302
    assert r.headers["location"].endswith("/dashboard")
    assert "session" in r.cookies                       # 세션 발급
    u = await _db.get_user_by_email("new@x.com")
    assert u is not None
    assert u["email_verified"] == 1                     # 제공자 검증 이메일
    assert (await _db.get_oauth_account("google", "g-1"))["user_id"] == u["id"]


@pytest.mark.asyncio
async def test_callback_links_to_existing_email(client, monkeypatch):
    """같은 이메일의 기존(비번) 계정이 있으면 새로 안 만들고 연결."""
    from backend.core.auth import hash_password
    uid = await _db.create_user("dup@x.com", hash_password("Str0ngPass!22"))
    monkeypatch.setattr(oauth_core, "google_exchange", _fake_exchange(sub="g-dup", email="dup@x.com"))
    r = await client.get("/api/auth/oauth/google/callback",
                         params={"code": "c", "state": "S"}, cookies={"oauth_state": "S"})
    assert r.status_code == 302 and "session" in r.cookies
    assert (await _db.get_user_by_email("dup@x.com"))["id"] == uid   # 동일 유저(중복 생성 X)
    assert (await _db.get_oauth_account("google", "g-dup"))["user_id"] == uid


@pytest.mark.asyncio
async def test_callback_returning_oauth_user_no_duplicate(client, monkeypatch):
    """이미 연결된 제공자 신원이면 같은 유저 재사용."""
    uid = await _db.create_user("ret@x.com", "")
    await _db.link_oauth_account("google", "g-ret", uid, "ret@x.com")
    monkeypatch.setattr(oauth_core, "google_exchange", _fake_exchange(sub="g-ret", email="ret@x.com"))
    r = await client.get("/api/auth/oauth/google/callback",
                         params={"code": "c", "state": "S"}, cookies={"oauth_state": "S"})
    assert r.status_code == 302 and "session" in r.cookies
    assert (await _db.get_oauth_account("google", "g-ret"))["user_id"] == uid


# ── callback sad ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_callback_state_mismatch_rejected(client, monkeypatch):
    """state(쿠키) ≠ state(쿼리) → CSRF 차단, 세션 없음."""
    monkeypatch.setattr(oauth_core, "google_exchange", _fake_exchange())
    r = await client.get("/api/auth/oauth/google/callback",
                         params={"code": "c", "state": "ATTACKER"}, cookies={"oauth_state": "REAL"})
    assert r.status_code == 302
    assert "/login?error=oauth_state" in r.headers["location"]
    assert "session" not in r.cookies


@pytest.mark.asyncio
async def test_callback_no_state_cookie_rejected(client, monkeypatch):
    monkeypatch.setattr(oauth_core, "google_exchange", _fake_exchange())
    r = await client.get("/api/auth/oauth/google/callback", params={"code": "c", "state": "S"})
    assert r.status_code == 302
    assert "/login?error=oauth_state" in r.headers["location"]


@pytest.mark.asyncio
async def test_callback_exchange_failure_redirects_error(client, monkeypatch):
    async def _boom(code):
        raise RuntimeError("token exchange failed")
    monkeypatch.setattr(oauth_core, "google_exchange", _boom)
    r = await client.get("/api/auth/oauth/google/callback",
                         params={"code": "c", "state": "S"}, cookies={"oauth_state": "S"})
    assert r.status_code == 302
    assert "/login?error=oauth_failed" in r.headers["location"]
    assert "session" not in r.cookies


@pytest.mark.asyncio
async def test_callback_unverified_email_rejected(client, monkeypatch):
    """제공자가 이메일 미검증으로 주면 계정 생성 안 함(스푸핑 방어)."""
    monkeypatch.setattr(oauth_core, "google_exchange", _fake_exchange(email="unv@x.com", verified=False))
    r = await client.get("/api/auth/oauth/google/callback",
                         params={"code": "c", "state": "S"}, cookies={"oauth_state": "S"})
    assert r.status_code == 302
    assert "/login?error=oauth_no_email" in r.headers["location"]
    assert await _db.get_user_by_email("unv@x.com") is None
