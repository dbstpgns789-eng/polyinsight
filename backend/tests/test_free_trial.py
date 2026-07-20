"""무료체험 배관 — 스키마·차감·환불·게이트."""
from __future__ import annotations

import pytest
import pytest_asyncio

from backend.core import db as _db
from backend.core.config import settings


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blobstore"))
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    await _db.migrate()
    yield


async def _mk_user(email: str = "free@test") -> int:
    return await _db.create_user(email, "hash")


@pytest.mark.asyncio
async def test_new_user_defaults_to_free_with_zero_used():
    uid = await _mk_user()
    user = await _db.get_user_by_id(uid)
    assert user["plan"] == "free"
    assert user["free_decks_used"] == 0
    assert user["onboarded_at"] is None


@pytest.mark.asyncio
async def test_consume_free_deck_increments():
    uid = await _mk_user()
    await _db.consume_free_deck(uid)
    user = await _db.get_user_by_id(uid)
    assert user["free_decks_used"] == 1


@pytest.mark.asyncio
async def test_refund_free_deck_decrements_but_never_below_zero():
    uid = await _mk_user()
    await _db.consume_free_deck(uid)
    await _db.refund_free_deck(uid)
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0
    # 이중 환불이 음수를 만들면 안 된다 — 무료 횟수가 늘어나는 버그가 된다
    await _db.refund_free_deck(uid)
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0


@pytest.mark.asyncio
async def test_paid_user_counter_untouched():
    """유료 유저는 무료 카운터를 소비하지 않는다 (게이트 대상이 아님)."""
    uid = await _mk_user("pro@test")
    await _db.set_plan(uid, "pro")
    await _db.consume_free_deck(uid)
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0


@pytest.mark.asyncio
async def test_mark_onboarded_is_idempotent():
    uid = await _mk_user()
    await _db.mark_onboarded(uid)
    first = (await _db.get_user_by_id(uid))["onboarded_at"]
    assert first is not None
    await _db.mark_onboarded(uid)
    assert (await _db.get_user_by_id(uid))["onboarded_at"] == first
