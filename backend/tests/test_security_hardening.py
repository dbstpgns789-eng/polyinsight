"""보안 하드닝 (2026-07-03) — 감사 20건 수정의 happy/sad path 검증.

커버: 업로드 유저별 쿼터(재정 DoS), 로그인 열거 대칭(429 vs 401), 세션 토큰 해싱,
HSTS, 프로덕션 fail-closed 시작가드, 흔한비번 차단, argon2 점진 재해싱.
"""
from __future__ import annotations

import hashlib

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import db as _db
from backend.core import ratelimit
from backend.core.config import settings
from backend.main import app

_TXT = {"file": ("x.txt", b"not a pdf", "text/plain")}
_CF = {"cf-connecting-ip": "9.9.9.9"}  # 로그인 rate limit은 CF 엣지 IP 있을 때만 적용


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'sec.db'}")
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "RENDER_TOKEN", "")
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    ratelimit.reset_all()
    await _db.migrate()
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── HIGH: 업로드 유저별 쿼터 (재정 DoS) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_quota_unverified_blocked(client, monkeypatch):
    """미인증 계정은 낮은 상한. 한도 초과 시 429 (파이프라인 트리거 전 차단)."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "UPLOAD_UNVERIFIED_LIMIT", 1)
    await client.post("/api/auth/signup", json={"email": "q1@x.com", "password": "Str0ngPass!22"})
    r1 = await client.post("/api/upload", files=_TXT)   # 쿼터 통과 → non-pdf 400 (파이프라인 X)
    assert r1.status_code == 400
    r2 = await client.post("/api/upload", files=_TXT)   # 한도 초과 → 429
    assert r2.status_code == 429
    assert r2.json()["detail"]["code"] == "ERR-AUTH-429"


@pytest.mark.asyncio
async def test_upload_quota_verified_higher_limit(client, monkeypatch):
    """인증 계정은 더 높은 상한 — 미인증 한도(1)를 넘겨도 통과."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "UPLOAD_UNVERIFIED_LIMIT", 1)
    monkeypatch.setattr(settings, "UPLOAD_USER_LIMIT", 3)
    await client.post("/api/auth/signup", json={"email": "q2@x.com", "password": "Str0ngPass!22"})
    u = await _db.get_user_by_email("q2@x.com")
    await _db.set_email_verified(u["id"])  # 인증 승격
    codes = [(await client.post("/api/upload", files=_TXT)).status_code for _ in range(3)]
    assert codes == [400, 400, 400]        # 미인증이면 2번째부터 막혔을 것 → 인증이라 3회 통과
    r4 = await client.post("/api/upload", files=_TXT)
    assert r4.status_code == 429


@pytest.mark.asyncio
async def test_upload_quota_disabled_no_block(client):
    """RATE_LIMIT_ENABLED=False(기본 dev/테스트)면 쿼터 미적용."""
    await client.post("/api/auth/signup", json={"email": "q3@x.com", "password": "Str0ngPass!22"})
    for _ in range(5):
        r = await client.post("/api/upload", files=_TXT)
        assert r.status_code == 400   # 전부 non-pdf 400, 429 없음


# ── MEDIUM: 로그인 열거 대칭 (부재 이메일도 429) ────────────────────────────

@pytest.mark.asyncio
async def test_login_absent_email_returns_429_not_401(client, monkeypatch):
    """부재 이메일도 한도 초과 시 429 → 상태코드(401 vs 429) 열거 오라클 차단."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "LOGIN_EMAIL_LIMIT", 3)
    monkeypatch.setattr(settings, "LOGIN_IP_LIMIT", 100)  # IP 한도는 방해 안 되게
    last = None
    for _ in range(3):
        last = await client.post("/api/auth/login",
                                 json={"email": "ghost@x.com", "password": "whatever12"}, headers=_CF)
    assert last.status_code == 429   # 예전엔 부재 이메일은 항상 401이었음
    assert last.json()["detail"]["code"] == "ERR-AUTH-429"


# ── MEDIUM: 세션 토큰 DB 해싱 ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_token_stored_hashed():
    """DB엔 sha256만, 쿠키 원문으로 조회는 정상."""
    import aiosqlite
    from backend.core.db import _db_path, _hash_token
    uid = await _db.create_user("h@x.com", "hash")
    await _db.create_session("plain-abc", uid, ttl_hours=72)
    async with aiosqlite.connect(_db_path()) as conn:
        async with conn.execute("SELECT token FROM sessions") as cur:
            stored = (await cur.fetchone())[0]
    assert stored != "plain-abc"                       # 평문 저장 안 함
    assert stored == _hash_token("plain-abc")          # sha256 저장
    assert (await _db.get_valid_session("plain-abc")) is not None  # 원문 조회 정상
    assert (await _db.get_valid_session("wrong")) is None


# ── MEDIUM/INFO: HSTS + 프로덕션 fail-closed 가드 ────────────────────────────

@pytest.mark.asyncio
async def test_hsts_only_when_secure(client, monkeypatch):
    r_dev = await client.get("/api/auth/me")  # dev(COOKIE_SECURE False) → HSTS 없음
    assert "strict-transport-security" not in {k.lower() for k in r_dev.headers}
    monkeypatch.setattr(settings, "COOKIE_SECURE", True)
    r_sec = await client.get("/api/auth/me")
    assert "strict-transport-security" in {k.lower() for k in r_sec.headers}


def test_validate_prod_config_fail_closed(monkeypatch):
    from backend.main import _validate_prod_config
    # https 오리진 + COOKIE_SECURE False → 시작 실패
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", "https://poly.example.com")
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "")
    monkeypatch.setattr(settings, "RENDER_TOKEN", "")
    with pytest.raises(RuntimeError):
        _validate_prod_config()
    # 전부 갖추면 통과
    monkeypatch.setattr(settings, "COOKIE_SECURE", True)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://poly.example.com")
    monkeypatch.setattr(settings, "RENDER_TOKEN", "rt")
    _validate_prod_config()
    # http-only dev면 insecure여도 통과(강제 안 함)
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", "http://localhost:3000")
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "")
    _validate_prod_config()


# ── LOW: 흔한 비밀번호 차단 ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signup_common_password_rejected(client):
    for weak in ("password", "12345678", "Password1"):  # 대소문자 무관
        r = await client.post("/api/auth/signup", json={"email": f"{weak}@x.com", "password": weak})
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "ERR-AUTH-007"


@pytest.mark.asyncio
async def test_signup_strong_password_accepted(client):
    r = await client.post("/api/auth/signup", json={"email": "strong@x.com", "password": "Str0ngPass!22"})
    assert r.status_code == 200


# ── INFO: argon2 점진 재해싱 ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_password_rehashed_on_login(client):
    """약한 파라미터 해시로 저장된 유저가 로그인하면 기본 파라미터로 갱신."""
    from argon2 import PasswordHasher
    from backend.core.auth import needs_rehash
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
    h = weak.hash("Str0ngPass!22")
    uid = await _db.create_user("rehash@x.com", h)
    assert needs_rehash(h) is True
    login = await client.post("/api/auth/login", json={"email": "rehash@x.com", "password": "Str0ngPass!22"})
    assert login.status_code == 200
    updated = (await _db.get_user_by_id(uid))["password_hash"]
    assert updated != h
    assert needs_rehash(updated) is False
