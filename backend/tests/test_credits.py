import pytest_asyncio

from backend.core import db


@pytest_asyncio.fixture
async def _uid(tmp_path, monkeypatch):
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path / 't.db'}")
    await db.migrate()
    return await db.create_user("c@x.io", "")


async def test_default_zero(_uid):
    assert await db.get_credits(_uid) == 0


async def test_add_and_deduct(_uid):
    await db.add_credits(_uid, 20)
    assert await db.get_credits(_uid) == 20
    ok = await db.deduct_credits(_uid, 5)
    assert ok is True
    assert await db.get_credits(_uid) == 15


async def test_deduct_insufficient_returns_false(_uid):
    await db.add_credits(_uid, 3)
    ok = await db.deduct_credits(_uid, 5)   # 잔액 부족
    assert ok is False
    assert await db.get_credits(_uid) == 3   # 미차감
