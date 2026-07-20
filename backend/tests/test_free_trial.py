"""무료체험 배관 — 스키마·차감·환불·게이트."""
from __future__ import annotations

import aiosqlite
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
    """유료 유저는 무료 카운터를 소비하지 않는다 (게이트 대상이 아님, no-op이므로 False 반환)."""
    uid = await _mk_user("pro@test")
    await _db.set_plan(uid, "pro")
    assert await _db.consume_free_deck(uid) is False
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0


@pytest.mark.asyncio
async def test_consume_free_deck_returns_false_when_exhausted():
    """상한을 넘으면 소비가 일어나지 않는다 — 카운터도 안 오른다(check-then-act 레이스 차단)."""
    uid = await _mk_user("exhaust@test")
    assert await _db.consume_free_deck(uid) is True
    assert await _db.consume_free_deck(uid) is False
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 1


@pytest.mark.asyncio
async def test_mark_onboarded_is_idempotent():
    uid = await _mk_user()
    await _db.mark_onboarded(uid)
    first = (await _db.get_user_by_id(uid))["onboarded_at"]
    assert first is not None
    await _db.mark_onboarded(uid)
    assert (await _db.get_user_by_id(uid))["onboarded_at"] == first


async def _seed_old_users_schema(db_path: str, email: str) -> None:
    """구스키마(plan/free_decks_used/onboarded_at 없는 users) 직접 재현.
    migrate()는 CREATE TABLE IF NOT EXISTS라서 테이블이 아예 없어야 ALTER 백필 경로를 탄다
    (fixture의 선행 migrate()가 이미 신스키마로 만들어버리므로 별도 DB 파일에 재현한다)."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        await conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, "hash", "2020-01-01T00:00:00"),
        )
        await conn.commit()


@pytest.mark.asyncio
async def test_migrate_backfills_existing_users_to_lab_and_is_idempotent(tmp_path, monkeypatch):
    """구스키마 유저(게이트 도입 전부터 있던 계정) = plan='lab'(면제)+onboarded_at 백필 대상.
    재migrate해도 onboarded_at을 덮어쓰지 않아야 하고, 백필 후 신규유저는 여전히 free/None이어야 한다."""
    legacy_db = str(tmp_path / "legacy.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{legacy_db}")
    await _seed_old_users_schema(legacy_db, "legacy@test")

    await _db.migrate()
    legacy = await _db.get_user_by_id(1)
    assert legacy["plan"] == "lab"
    assert legacy["onboarded_at"] is not None

    # 재migrate — 멱등: onboarded_at 값이 안 바뀐다
    await _db.migrate()
    legacy_again = await _db.get_user_by_id(1)
    assert legacy_again["onboarded_at"] == legacy["onboarded_at"]

    # 백필 후 신규 유저는 DDL DEFAULT 경로 — 여전히 free/None (백필과 충돌 없음)
    new_uid = await _mk_user("newafterbackfill@test")
    new_user = await _db.get_user_by_id(new_uid)
    assert new_user["plan"] == "free"
    assert new_user["onboarded_at"] is None
