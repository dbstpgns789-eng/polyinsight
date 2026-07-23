import pytest_asyncio

from backend.core import db


@pytest_asyncio.fixture
async def _uid(tmp_path, monkeypatch):
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path / 't.db'}")
    await db.migrate()
    return await db.create_user("u@x.io", "")


async def test_upsert_then_get(_uid):
    await db.upsert_social_account(_uid, "instagram", "ig123", "myshop", "ENC_TOKEN", "2026-09-01T00:00:00")
    acct = await db.get_social_account(_uid, "instagram")
    assert acct["ig_user_id"] == "ig123"
    assert acct["ig_username"] == "myshop"
    assert acct["access_token"] == "ENC_TOKEN"


async def test_upsert_overwrites(_uid):
    await db.upsert_social_account(_uid, "instagram", "ig123", "old", "T1", "2026-09-01T00:00:00")
    await db.upsert_social_account(_uid, "instagram", "ig123", "new", "T2", "2026-10-01T00:00:00")
    acct = await db.get_social_account(_uid, "instagram")
    assert acct["ig_username"] == "new"
    assert acct["access_token"] == "T2"


async def test_get_missing_returns_none(_uid):
    assert await db.get_social_account(_uid, "instagram") is None


async def test_delete(_uid):
    await db.upsert_social_account(_uid, "instagram", "ig123", "s", "T", None)
    await db.delete_social_account(_uid, "instagram")
    assert await db.get_social_account(_uid, "instagram") is None
