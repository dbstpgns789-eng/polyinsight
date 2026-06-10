import json
from datetime import datetime, timedelta

import aiosqlite

from .config import settings


def _db_path() -> str:
    url = settings.DATABASE_URL
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///") :]
    if url.startswith("sqlite://"):
        return url[len("sqlite://") :]
    return url


def _utc_now() -> datetime:
    return datetime.utcnow()


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


async def migrate() -> None:
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA foreign_keys=ON;")
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                stage TEXT,
                progress INT,
                degraded INT,
                warnings TEXT,
                title TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS card_data (
                job_id TEXT PRIMARY KEY REFERENCES jobs(job_id),
                data_json TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS card_images (
                id INTEGER PRIMARY KEY,
                job_id TEXT,
                card_num INT,
                png_bytes BLOB,
                expires_at TEXT
            );

            CREATE TABLE IF NOT EXISTS exports (
                export_job_id TEXT PRIMARY KEY,
                job_id TEXT,
                zip_bytes BLOB,
                filename TEXT,
                expires_at TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK(id=1),
                org TEXT,
                dept TEXT,
                researcher TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS researchers (
                name TEXT PRIMARY KEY,
                photo_bytes BLOB,
                created_at TEXT
            );
            """
        )
        await conn.commit()


async def create_job(job_id: str, title: str | None) -> None:
    now = _utc_now_iso()
    warnings = json.dumps([])
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute(
            """
            INSERT INTO jobs (
                job_id, status, stage, progress, degraded, warnings, title, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, "PENDING", None, 0, 0, warnings, title, now, now),
        )
        await conn.commit()


async def get_job(job_id: str) -> dict | None:
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            data = dict(row)
            warnings = data.get("warnings")
            data["warnings"] = json.loads(warnings) if warnings else []
            return data


async def update_job(
    job_id: str,
    status: str,
    stage: str | None = None,
    progress: int | None = None,
    degraded: bool | None = None,
    warnings: list[str] | None = None,
) -> None:
    fields = ["status = ?"]
    params: list[object] = [status]
    if stage is not None:
        fields.append("stage = ?")
        params.append(stage)
    if progress is not None:
        fields.append("progress = ?")
        params.append(progress)
    if degraded is not None:
        fields.append("degraded = ?")
        params.append(1 if degraded else 0)
    if warnings is not None:
        fields.append("warnings = ?")
        params.append(json.dumps(warnings))
    fields.append("updated_at = ?")
    params.append(_utc_now_iso())
    params.append(job_id)
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute(
            f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?", params
        )
        await conn.commit()


# 하위 호환 alias
async def update_job_status(
    job_id: str,
    status: str,
    stage: str | None = None,
    progress: int | None = None,
) -> None:
    fields = ["status = ?"]
    params: list[object] = [status]

    if stage is not None:
        fields.append("stage = ?")
        params.append(stage)
    if progress is not None:
        fields.append("progress = ?")
        params.append(progress)

    fields.append("updated_at = ?")
    params.append(_utc_now_iso())
    params.append(job_id)

    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute(
            f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?",
            params,
        )
        await conn.commit()


async def append_warning(job_id: str, warning: str) -> None:
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT warnings FROM jobs WHERE job_id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
        warnings = []
        if row and row["warnings"]:
            warnings = json.loads(row["warnings"])
        warnings.append(warning)
        await conn.execute(
            "UPDATE jobs SET warnings = ?, updated_at = ? WHERE job_id = ?",
            (json.dumps(warnings), _utc_now_iso(), job_id),
        )
        await conn.commit()


async def save_card_data(job_id: str, card_data_json: str) -> None:
    now = _utc_now_iso()
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute(
            """
            INSERT INTO card_data (job_id, data_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                data_json = excluded.data_json,
                updated_at = excluded.updated_at
            """,
            (job_id, card_data_json, now),
        )
        await conn.commit()


async def get_card_data(job_id: str) -> str | None:
    async with aiosqlite.connect(_db_path()) as conn:
        async with conn.execute(
            "SELECT data_json FROM card_data WHERE job_id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def update_job_title(job_id: str, title: str) -> bool:
    """job 표시명(title) 갱신. 존재하면 True."""
    async with aiosqlite.connect(_db_path()) as conn:
        cursor = await conn.execute(
            "UPDATE jobs SET title = ?, updated_at = ? WHERE job_id = ?",
            (title, _utc_now().isoformat(), job_id),
        )
        await conn.commit()
        return (cursor.rowcount or 0) > 0


async def delete_job(job_id: str) -> bool:
    """job과 연관 데이터(card_data·card_images·exports) 일괄 삭제. job 존재 시 True."""
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute("DELETE FROM card_images WHERE job_id = ?", (job_id,))
        await conn.execute("DELETE FROM card_data WHERE job_id = ?", (job_id,))
        await conn.execute("DELETE FROM exports WHERE job_id = ?", (job_id,))
        cursor = await conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        await conn.commit()
        return (cursor.rowcount or 0) > 0


async def save_card_image(
    job_id: str,
    card_num: int,
    png_bytes: bytes,
    ttl_hours: int = 24,
) -> None:
    expires_at = (_utc_now() + timedelta(hours=ttl_hours)).isoformat()
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute(
            "DELETE FROM card_images WHERE job_id = ? AND card_num = ?",
            (job_id, card_num),
        )
        await conn.execute(
            """
            INSERT INTO card_images (job_id, card_num, png_bytes, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, card_num, png_bytes, expires_at),
        )
        await conn.commit()


async def get_card_images(job_id: str) -> dict[int, bytes]:
    now = _utc_now_iso()
    images: dict[int, bytes] = {}
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            """
            SELECT card_num, png_bytes
            FROM card_images
            WHERE job_id = ? AND expires_at > ?
            """,
            (job_id, now),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                if row["png_bytes"] is not None:
                    images[row["card_num"]] = row["png_bytes"]
    return images


async def save_export(
    export_job_id: str,
    job_id: str,
    zip_bytes: bytes,
    filename: str,
    ttl_hours: int = 24,
) -> None:
    now = _utc_now_iso()
    expires_at = (_utc_now() + timedelta(hours=ttl_hours)).isoformat()
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute(
            """
            INSERT INTO exports (
                export_job_id, job_id, zip_bytes, filename, expires_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(export_job_id) DO UPDATE SET
                job_id = excluded.job_id,
                zip_bytes = excluded.zip_bytes,
                filename = excluded.filename,
                expires_at = excluded.expires_at,
                created_at = excluded.created_at
            """,
            (export_job_id, job_id, zip_bytes, filename, expires_at, now),
        )
        await conn.commit()


async def get_export(export_job_id: str) -> dict | None:
    now = _utc_now_iso()
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            """
            SELECT * FROM exports
            WHERE export_job_id = ? AND expires_at > ?
            """,
            (export_job_id, now),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def cleanup_expired_blobs() -> int:
    now = _utc_now_iso()
    deleted = 0
    async with aiosqlite.connect(_db_path()) as conn:
        cursor = await conn.execute(
            "DELETE FROM card_images WHERE expires_at <= ?",
            (now,),
        )
        deleted += cursor.rowcount or 0
        cursor = await conn.execute(
            "DELETE FROM exports WHERE expires_at <= ?",
            (now,),
        )
        deleted += cursor.rowcount or 0
        await conn.commit()
    return deleted


async def list_jobs(limit: int = 20, offset: int = 0) -> list[dict]:
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            """
            SELECT * FROM jobs
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()

    jobs: list[dict] = []
    for row in rows:
        data = dict(row)
        warnings = data.get("warnings")
        data["warnings"] = json.loads(warnings) if warnings else []
        jobs.append(data)
    return jobs
