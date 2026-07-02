"""rate limit — 인메모리 리미터 단위 + 로그인 엔드포인트 429 통합."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import db as _db
from backend.core import ratelimit
from backend.core.config import settings
from backend.main import app


# ── 단위: check / record / clear ────────────────────────────────────────────

def test_check_blocks_at_limit(monkeypatch):
    ratelimit.reset_all()
    t = [1000.0]
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: t[0])
    for _ in range(3):
        assert ratelimit.check("k", 3, 60) is None
        ratelimit.record("k")
    ra = ratelimit.check("k", 3, 60)      # 4번째 = 차단
    assert ra is not None and ra > 0


def test_window_expiry_frees(monkeypatch):
    ratelimit.reset_all()
    t = [1000.0]
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: t[0])
    for _ in range(3):
        ratelimit.record("k")
    assert ratelimit.check("k", 3, 60) is not None
    t[0] += 61                             # window 경과
    assert ratelimit.check("k", 3, 60) is None


def test_clear_resets(monkeypatch):
    ratelimit.reset_all()
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: 5.0)
    for _ in range(3):
        ratelimit.record("k")
    ratelimit.clear("k")
    assert ratelimit.check("k", 3, 60) is None


# ── 통합: 로그인 429 ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'rl.db'}")
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "LOGIN_IP_LIMIT", 3)
    monkeypatch.setattr(settings, "LOGIN_IP_WINDOW_S", 300)
    ratelimit.reset_all()
    await _db.migrate()
    yield


# rate limit은 CF 엣지 IP(cf-connecting-ip)가 있을 때만 적용 → 테스트는 헤더로 공개 IP 흉내.
_CF = {"cf-connecting-ip": "9.9.9.9"}


@pytest.mark.asyncio
async def test_login_ip_rate_limited():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        last = None
        for _ in range(4):
            last = await c.post("/api/auth/login", json={"email": "x@y.com", "password": "nope1234"}, headers=_CF)
        assert last.status_code == 429
        assert last.json()["detail"]["code"] == "ERR-AUTH-429"
        assert int(last.headers["retry-after"]) > 0


@pytest.mark.asyncio
async def test_no_cf_header_not_limited():
    """cf-connecting-ip 없으면(dev/내부) rate limit 미적용 — dev 악화 방지."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        last = None
        for _ in range(6):  # LOGIN_IP_LIMIT=3보다 많이
            last = await c.post("/api/auth/login", json={"email": "x@y.com", "password": "nope1234"})
        assert last.status_code == 401  # 429 아님


@pytest.mark.asyncio
async def test_correct_password_never_locked_out(monkeypatch):
    """CONFIRMED 수정 검증 — 공격자가 오답으로 이메일 한도를 채워도 정답 로그인은 통과."""
    monkeypatch.setattr(settings, "LOGIN_EMAIL_LIMIT", 3)
    monkeypatch.setattr(settings, "LOGIN_IP_LIMIT", 1000)  # IP 한도는 방해 안 되게
    from backend.core.auth import hash_password
    await _db.create_user("victim@y.com", hash_password("password1"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        for _ in range(5):  # 공격자 오답 5회 → 이메일 카운터 초과
            await c.post("/api/auth/login", json={"email": "victim@y.com", "password": "wrongwrong"}, headers=_CF)
        # 피해자 정답 → 잠기면 안 됨(200)
        ok = await c.post("/api/auth/login", json={"email": "victim@y.com", "password": "password1"}, headers=_CF)
        assert ok.status_code == 200
        assert "session" in ok.cookies
