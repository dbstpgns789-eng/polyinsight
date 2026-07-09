"""BLOB→파일 이주 스크립트 — 구스키마 BLOB 행을 디스크로 옮기고 storage_key 세팅, 멱등."""
from __future__ import annotations

import aiosqlite
import pytest

from backend.core import db as _db
from backend.core import storage as _storage
from backend.core.config import settings
from backend.scripts.migrate_blobs_to_disk import migrate_blobs


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'm.db'}")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blob"))


async def _seed_old_card_row(job_id: str, card_num: int, png: bytes):
    # 구스키마: png_bytes 컬럼이 있고 storage_key는 비어있는 상태를 재현.
    async with aiosqlite.connect(_db._db_path()) as conn:
        await conn.execute("ALTER TABLE card_images ADD COLUMN png_bytes BLOB")
        await conn.execute(
            "INSERT INTO card_images (job_id, card_num, png_bytes, storage_key, expires_at) "
            "VALUES (?, ?, ?, NULL, ?)",
            (job_id, card_num, png, "2999-01-01T00:00:00"),
        )
        await conn.commit()


@pytest.mark.asyncio
async def test_migrate_moves_blob_to_disk_and_is_idempotent():
    await _db.migrate()
    await _db.create_job("j1", "p.pdf", user_id=1)
    await _seed_old_card_row("j1", 1, b"\x89PNG-old")

    moved = await migrate_blobs()
    assert moved >= 1
    # 파일이 디스크에, storage_key 세팅, BLOB 컬럼 제거됨
    assert await _storage.get_storage().get("jobs/j1/cards/1.png") == b"\x89PNG-old"
    imgs = await _db.get_card_images("j1")
    assert imgs == {1: b"\x89PNG-old"}
    async with aiosqlite.connect(_db._db_path()) as conn:
        async with conn.execute("PRAGMA table_info(card_images)") as cur:
            cols = [r[1] for r in await cur.fetchall()]
    assert "png_bytes" not in cols     # 컬럼 drop 확인

    # 재실행 멱등 — 이미 이주됨, 예외 없이 0건
    again = await migrate_blobs()
    assert again == 0


def test_backup_assets_snapshots_only_assets(tmp_path):
    """L1 백업 확장: 영속 assets/만 tar에 담고 TTL 재생성 가능한 cards/는 제외. 대상 없으면 None."""
    import tarfile
    from backend.scripts.backup_db import backup_assets
    storage = tmp_path / "blob"
    (storage / "jobs" / "j1" / "assets").mkdir(parents=True)
    (storage / "jobs" / "j1" / "assets" / "a.png").write_bytes(b"x")
    (storage / "jobs" / "j1" / "cards").mkdir(parents=True)
    (storage / "jobs" / "j1" / "cards" / "1.png").write_bytes(b"y")
    dest = tmp_path / "bk"
    out = backup_assets(str(storage), str(dest))
    assert out is not None
    with tarfile.open(out) as tar:
        names = tar.getnames()
    assert any(n.endswith("assets/a.png") for n in names)   # 자산 포함
    assert not any("cards" in n for n in names)              # cards 제외
    assert backup_assets(str(tmp_path / "empty"), str(dest)) is None  # 대상 없으면 None
