"""L1 일회성 이주 — SQLite BLOB(card_images·exports·deck_assets)을 Storage(파일)로 이동.

멱등: storage_key가 이미 있는 행은 skip. 전 행 이주 후 BLOB 컬럼 DROP.
운영: 서버 정지 → (backup_db) → 이 스크립트 → 새 코드 배포 → 기동.
researchers.photo_bytes는 유령 컬럼이라 범위 밖.

사용법(루트에서): PYTHONUTF8=1 .venv/Scripts/python.exe -m backend.scripts.migrate_blobs_to_disk
"""
from __future__ import annotations

import asyncio

import aiosqlite

from backend.core import db as _db
from backend.core.storage import get_storage

# (테이블, BLOB 컬럼, 키 생성기(row)->key)
_SPECS = [
    ("card_images", "png_bytes", lambda r: f"jobs/{r['job_id']}/cards/{r['card_num']}.png"),
    ("exports", "zip_bytes", lambda r: f"jobs/{r['job_id']}/exports/{r['export_job_id']}.zip"),
    ("deck_assets", "bytes", lambda r: f"jobs/{r['job_id']}/assets/{r['asset_id']}"),
]


async def _has_column(conn: aiosqlite.Connection, table: str, col: str) -> bool:
    async with conn.execute(f"PRAGMA table_info({table})") as cur:
        return col in [row[1] for row in await cur.fetchall()]


async def migrate_blobs() -> int:
    """BLOB 행을 파일로 이동. 반환=이동 건수. 멱등(재실행 시 남은 것만)."""
    await _db.migrate()   # storage_key 컬럼 보장(멱등 ALTER)
    storage = get_storage()
    moved = 0
    for table, blob_col, keyfn in _SPECS:
        async with aiosqlite.connect(_db._db_path()) as conn:
            conn.row_factory = aiosqlite.Row
            if not await _has_column(conn, table, blob_col):
                continue  # 이미 이주 완료(컬럼 drop됨) 또는 신규 스키마
            async with conn.execute(
                f"SELECT * FROM {table} "
                f"WHERE storage_key IS NULL AND {blob_col} IS NOT NULL"
            ) as cur:
                rows = [dict(r) for r in await cur.fetchall()]
            for r in rows:
                await storage.put(keyfn(r), r[blob_col])
                moved += 1
            if rows:
                async with aiosqlite.connect(_db._db_path()) as wconn:
                    for r in rows:
                        if table == "card_images":
                            await wconn.execute(
                                "UPDATE card_images SET storage_key=? WHERE job_id=? AND card_num=?",
                                (keyfn(r), r["job_id"], r["card_num"]),
                            )
                        elif table == "exports":
                            await wconn.execute(
                                "UPDATE exports SET storage_key=? WHERE export_job_id=?",
                                (keyfn(r), r["export_job_id"]),
                            )
                        else:  # deck_assets
                            await wconn.execute(
                                "UPDATE deck_assets SET storage_key=? WHERE job_id=? AND asset_id=?",
                                (keyfn(r), r["job_id"], r["asset_id"]),
                            )
                    await wconn.commit()
            # 전 행 이주 후 BLOB 컬럼 DROP(sqlite ≥3.35).
            async with aiosqlite.connect(_db._db_path()) as dconn:
                async with dconn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {blob_col} IS NOT NULL AND storage_key IS NULL"
                ) as cur:
                    remaining = (await cur.fetchone())[0]
                if remaining == 0:
                    await dconn.execute(f"ALTER TABLE {table} DROP COLUMN {blob_col}")
                    await dconn.commit()
    return moved


async def _main() -> None:
    n = await migrate_blobs()
    print(f"이주 완료: {n}건 파일로 이동, BLOB 컬럼 정리됨.")


if __name__ == "__main__":
    asyncio.run(_main())
