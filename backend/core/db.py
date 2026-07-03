import hashlib
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import aiosqlite

from .config import settings


def _hash_token(token: str) -> str:
    """세션 토큰은 DB에 sha256으로만 저장(auth_tokens와 동일 패턴). 쿠키엔 원문 유지.
    DB/백업 유출 시 세션 원문 부재 → 재사용 불가(탈취 방어)."""
    return hashlib.sha256(token.encode()).hexdigest()


def _db_path() -> str:
    url = settings.DATABASE_URL
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///") :]
    if url.startswith("sqlite://"):
        return url[len("sqlite://") :]
    return url


@asynccontextmanager
async def _connect():
    """모든 DB 접근의 중앙 연결 지점. busy_timeout으로 동시 쓰기 시 SQLITE_BUSY 즉사 방지."""
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute("PRAGMA busy_timeout=5000;")
        yield conn


def _utc_now() -> datetime:
    return datetime.utcnow()


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


async def migrate() -> None:
    async with _connect() as conn:
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
                user_id INTEGER,
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

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                purpose TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS invites (
                code TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                used_by INTEGER REFERENCES users(id),
                used_at TEXT
            );

            -- 소셜 로그인(2026-07-03): 제공자 신원 ↔ users 연결. 한 유저가 여러 제공자 가능.
            CREATE TABLE IF NOT EXISTS oauth_accounts (
                provider TEXT NOT NULL,
                provider_user_id TEXT NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id),
                email TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (provider, provider_user_id)
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT NOT NULL,
                job_id TEXT,
                payload TEXT,
                created_at TEXT NOT NULL
            );

            -- 헌법 v3.0 단일 저작 경로(레거시 card_data와 분리). HTML 덱 전문 + 충실성 검증 결과.
            -- paper_text: 편집본 재검증(V)을 위한 원문 보관 (Phase 3).
            CREATE TABLE IF NOT EXISTS authored_deck (
                job_id TEXT PRIMARY KEY REFERENCES jobs(job_id),
                html TEXT,
                verify_json TEXT,
                card_count INT,
                paper_text TEXT,
                updated_at TEXT
            );

            -- 덱 이미지 삽입(스펙 2026-07-01): 바이트 원장. 저장 HTML엔 URL만, 렌더시 인라인.
            CREATE TABLE IF NOT EXISTS deck_assets (
                asset_id TEXT,
                job_id TEXT REFERENCES jobs(job_id),
                bytes BLOB,
                mime TEXT,
                source_type TEXT,
                source_url TEXT,
                provider TEXT,
                credit TEXT,
                credit_url TEXT,
                created_at TEXT,
                expires_at TEXT,
                PRIMARY KEY (job_id, asset_id)
            );
            """
        )
        # idempotent 마이그레이션 — 기존 DB의 authored_deck에 paper_text 없으면 추가.
        async with conn.execute("PRAGMA table_info(authored_deck)") as cur:
            cols = [row[1] for row in await cur.fetchall()]
        if "paper_text" not in cols:
            await conn.execute("ALTER TABLE authored_deck ADD COLUMN paper_text TEXT")
        # 유저별 격리(2026-07-02) — 기존 jobs에 user_id 없으면 추가(backfill은 별도 스크립트).
        async with conn.execute("PRAGMA table_info(jobs)") as cur:
            jcols = [row[1] for row in await cur.fetchall()]
        if "user_id" not in jcols:
            await conn.execute("ALTER TABLE jobs ADD COLUMN user_id INTEGER")
        # 이메일 인증(2026-07-02) — 기존 users에 email_verified 없으면 추가(기존행=0=미인증, grace라 비차단).
        async with conn.execute("PRAGMA table_info(users)") as cur:
            ucols = [row[1] for row in await cur.fetchall()]
        if "email_verified" not in ucols:
            await conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        await conn.commit()


async def create_job(job_id: str, title: str | None, user_id: int | None = None) -> None:
    now = _utc_now_iso()
    warnings = json.dumps([])
    async with _connect() as conn:
        await conn.execute(
            """
            INSERT INTO jobs (
                job_id, status, stage, progress, degraded, warnings, title, user_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, "PENDING", None, 0, 0, warnings, title, user_id, now, now),
        )
        await conn.commit()


async def get_job(job_id: str) -> dict | None:
    async with _connect() as conn:
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
    async with _connect() as conn:
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

    async with _connect() as conn:
        await conn.execute(
            f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?",
            params,
        )
        await conn.commit()


async def append_warning(job_id: str, warning: str) -> None:
    async with _connect() as conn:
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
    async with _connect() as conn:
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
    async with _connect() as conn:
        async with conn.execute(
            "SELECT data_json FROM card_data WHERE job_id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def card_data_job_ids(job_ids: list[str]) -> set[str]:
    """card_data 행 보유 잡 = 옛(legacy) 파이프라인 산출물. 목록의 kind 판정용."""
    if not job_ids:
        return set()
    placeholders = ",".join("?" * len(job_ids))
    async with _connect() as conn:
        async with conn.execute(
            f"SELECT job_id FROM card_data WHERE job_id IN ({placeholders})", job_ids
        ) as cursor:
            return {row[0] for row in await cursor.fetchall()}


# ── 단일 저작 덱 (헌법 v3.0) ───────────────────────────────────────────────

async def save_authored_deck(
    job_id: str,
    html: str,
    verify_json: str,
    card_count: int,
    paper_text: str | None = None,
) -> None:
    """덱 저장. paper_text=None(편집 저장)이면 기존 원문을 보존(덮어쓰지 않음)."""
    now = _utc_now_iso()
    async with _connect() as conn:
        await conn.execute(
            """
            INSERT INTO authored_deck (job_id, html, verify_json, card_count, paper_text, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                html = excluded.html,
                verify_json = excluded.verify_json,
                card_count = excluded.card_count,
                paper_text = COALESCE(excluded.paper_text, authored_deck.paper_text),
                updated_at = excluded.updated_at
            """,
            (job_id, html, verify_json, card_count, paper_text, now),
        )
        await conn.commit()


async def get_authored_deck(job_id: str) -> dict | None:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT html, verify_json, card_count, paper_text, updated_at "
            "FROM authored_deck WHERE job_id = ?",
            (job_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ── 덱 이미지 자산 (스펙 2026-07-01) ─────────────────────────────────────────

async def save_deck_asset(
    job_id: str,
    asset_id: str,
    data: bytes,
    mime: str,
    source_type: str = "upload-owned",
    source_url: str | None = None,
    provider: str | None = None,
    credit: str | None = None,
    credit_url: str | None = None,
    ttl_hours: int = 24 * 30,  # 덱 수명 정합(스펙 §4.4). 재편집까지 생존.
) -> None:
    now = _utc_now_iso()
    expires_at = (_utc_now() + timedelta(hours=ttl_hours)).isoformat()
    async with _connect() as conn:
        await conn.execute(
            """
            INSERT INTO deck_assets (
                asset_id, job_id, bytes, mime, source_type, source_url,
                provider, credit, credit_url, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, asset_id) DO UPDATE SET
                bytes = excluded.bytes, mime = excluded.mime,
                source_type = excluded.source_type, source_url = excluded.source_url,
                provider = excluded.provider, credit = excluded.credit,
                credit_url = excluded.credit_url, expires_at = excluded.expires_at
            """,
            (asset_id, job_id, data, mime, source_type, source_url,
             provider, credit, credit_url, now, expires_at),
        )
        await conn.commit()


async def get_deck_asset(job_id: str, asset_id: str) -> dict | None:
    now = _utc_now_iso()
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT asset_id, bytes, mime, source_type, source_url, provider, "
            "credit, credit_url FROM deck_assets "
            "WHERE job_id = ? AND asset_id = ? AND expires_at > ?",
            (job_id, asset_id, now),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_deck_assets(job_id: str) -> list[dict]:
    now = _utc_now_iso()
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT asset_id, mime, source_type FROM deck_assets "
            "WHERE job_id = ? AND expires_at > ?",
            (job_id, now),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def recover_stale_jobs() -> int:
    """서버 시작 시 고아 잡 회수. startup 시점엔 이 프로세스가 만든 잡이 아직 없으므로
    PENDING/RUNNING = 전부 이전 프로세스의 고아 — 시간 조건 불필요.
    (단일 프로세스 운영 전제 — 다중 프로세스면 살아있는 잡을 오판할 수 있음)"""
    warnings = json.dumps(["서버 재시작으로 작업이 중단되었습니다. 다시 업로드해 주세요."])
    async with _connect() as conn:
        cursor = await conn.execute(
            "UPDATE jobs SET status = 'ERROR', warnings = ?, updated_at = ? "
            "WHERE status IN ('PENDING', 'RUNNING')",
            (warnings, _utc_now_iso()),
        )
        await conn.commit()
        return cursor.rowcount or 0


async def update_job_title(job_id: str, title: str) -> bool:
    """job 표시명(title) 갱신. 존재하면 True."""
    async with _connect() as conn:
        cursor = await conn.execute(
            "UPDATE jobs SET title = ?, updated_at = ? WHERE job_id = ?",
            (title, _utc_now().isoformat(), job_id),
        )
        await conn.commit()
        return (cursor.rowcount or 0) > 0


async def delete_job(job_id: str) -> bool:
    """job과 연관 데이터(card_data·card_images·exports·authored_deck) 일괄 삭제. job 존재 시 True."""
    async with _connect() as conn:
        await conn.execute("DELETE FROM card_images WHERE job_id = ?", (job_id,))
        await conn.execute("DELETE FROM deck_assets WHERE job_id = ?", (job_id,))
        await conn.execute("DELETE FROM card_data WHERE job_id = ?", (job_id,))
        await conn.execute("DELETE FROM exports WHERE job_id = ?", (job_id,))
        await conn.execute("DELETE FROM authored_deck WHERE job_id = ?", (job_id,))
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
    async with _connect() as conn:
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


async def delete_card_images_above(job_id: str, max_card_num: int) -> None:
    """card_num > max_card_num 인 카드 이미지 삭제 (편집으로 카드 수가 줄었을 때 잔재 정리)."""
    async with _connect() as conn:
        await conn.execute(
            "DELETE FROM card_images WHERE job_id = ? AND card_num > ?",
            (job_id, max_card_num),
        )
        await conn.commit()


async def get_card_images(job_id: str) -> dict[int, bytes]:
    now = _utc_now_iso()
    images: dict[int, bytes] = {}
    async with _connect() as conn:
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
    async with _connect() as conn:
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
    async with _connect() as conn:
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
    async with _connect() as conn:
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
        # 만료 세션 정리(무한증식 방지, 2026-07-02) — _ttl_cleaner가 30분마다 호출.
        cursor = await conn.execute(
            "DELETE FROM sessions WHERE expires_at <= ?",
            (now,),
        )
        deleted += cursor.rowcount or 0
        # 만료·사용 완료된 인증 토큰 정리.
        cursor = await conn.execute(
            "DELETE FROM auth_tokens WHERE expires_at <= ? OR used_at IS NOT NULL",
            (now,),
        )
        deleted += cursor.rowcount or 0
        await conn.commit()
    return deleted


async def list_jobs(limit: int = 20, offset: int = 0, user_id: int | None = None) -> list[dict]:
    where = "WHERE user_id = ?" if user_id is not None else ""
    params: list[object] = ([user_id] if user_id is not None else []) + [limit, offset]
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            f"""
            SELECT * FROM jobs
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ) as cursor:
            rows = await cursor.fetchall()

    jobs: list[dict] = []
    for row in rows:
        data = dict(row)
        warnings = data.get("warnings")
        data["warnings"] = json.loads(warnings) if warnings else []
        jobs.append(data)
    return jobs


# ── 인증: users / sessions / invites ──────────────────────────────────────

async def create_user(email: str, password_hash: str, role: str = "user") -> int:
    now = _utc_now_iso()
    async with _connect() as conn:
        cursor = await conn.execute(
            "INSERT INTO users (email, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (email, password_hash, role, now),
        )
        await conn.commit()
        return int(cursor.lastrowid)


async def get_user_by_email(email: str) -> dict | None:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM users WHERE email = ?", (email,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_by_id(user_id: int) -> dict | None:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_session(token: str, user_id: int, ttl_hours: int) -> None:
    now = _utc_now()
    expires_at = (now + timedelta(hours=ttl_hours)).isoformat()
    async with _connect() as conn:
        await conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (_hash_token(token), user_id, now.isoformat(), expires_at),
        )
        await conn.commit()


async def get_valid_session(token: str) -> dict | None:
    now = _utc_now_iso()
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM sessions WHERE token = ? AND expires_at > ?", (_hash_token(token), now)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def delete_session(token: str) -> None:
    async with _connect() as conn:
        await conn.execute("DELETE FROM sessions WHERE token = ?", (_hash_token(token),))
        await conn.commit()


async def delete_sessions_by_user(user_id: int) -> int:
    """유저의 전 세션 무효화 — 비밀번호 재설정 시 탈취 세션 강제 로그아웃."""
    async with _connect() as conn:
        cursor = await conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        await conn.commit()
        return cursor.rowcount or 0


async def update_password_hash(user_id: int, password_hash: str) -> None:
    async with _connect() as conn:
        await conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        await conn.commit()


async def create_invite(code: str) -> None:
    now = _utc_now_iso()
    async with _connect() as conn:
        await conn.execute(
            "INSERT INTO invites (code, created_at, used_by, used_at) VALUES (?, ?, NULL, NULL)",
            (code, now),
        )
        await conn.commit()


async def get_invite(code: str) -> dict | None:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM invites WHERE code = ?", (code,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def consume_invite(code: str, user_id: int) -> bool:
    """미사용 초대코드면 사용 처리하고 True. 없거나 이미 사용됐으면 False."""
    now = _utc_now_iso()
    async with _connect() as conn:
        cursor = await conn.execute(
            "UPDATE invites SET used_by = ?, used_at = ? WHERE code = ? AND used_by IS NULL",
            (user_id, now, code),
        )
        await conn.commit()
        return (cursor.rowcount or 0) > 0


# ── 소셜 로그인: oauth_accounts (2026-07-03) ───────────────────────────────

async def get_oauth_account(provider: str, provider_user_id: str) -> dict | None:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM oauth_accounts WHERE provider = ? AND provider_user_id = ?",
            (provider, provider_user_id),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def link_oauth_account(provider: str, provider_user_id: str, user_id: int, email: str | None) -> None:
    now = _utc_now_iso()
    async with _connect() as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO oauth_accounts (provider, provider_user_id, user_id, email, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (provider, provider_user_id, user_id, email, now),
        )
        await conn.commit()


# ── 이메일 인증: auth_tokens (2026-07-02) ──────────────────────────────────
# 원문 토큰은 이메일 링크에만, DB엔 sha256만(누출 시 방어). 단일사용·TTL.

async def create_auth_token(token_hash: str, user_id: int, purpose: str, ttl_hours: int) -> None:
    now = _utc_now()
    expires_at = (now + timedelta(hours=ttl_hours)).isoformat()
    async with _connect() as conn:
        await conn.execute(
            "INSERT INTO auth_tokens (token_hash, user_id, purpose, created_at, expires_at, used_at) "
            "VALUES (?, ?, ?, ?, ?, NULL)",
            (token_hash, user_id, purpose, now.isoformat(), expires_at),
        )
        await conn.commit()


async def get_auth_token(token_hash: str, purpose: str) -> dict | None:
    """미사용·미만료·purpose 일치 토큰만 반환."""
    now = _utc_now_iso()
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM auth_tokens WHERE token_hash = ? AND purpose = ? "
            "AND used_at IS NULL AND expires_at > ?",
            (token_hash, purpose, now),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def mark_token_used(token_hash: str) -> None:
    async with _connect() as conn:
        await conn.execute(
            "UPDATE auth_tokens SET used_at = ? WHERE token_hash = ?",
            (_utc_now_iso(), token_hash),
        )
        await conn.commit()


async def set_email_verified(user_id: int) -> None:
    async with _connect() as conn:
        await conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
        await conn.commit()


# ── 행동 로깅: events ──────────────────────────────────────────────────────

async def log_event(
    event_type: str,
    user_id: int | None = None,
    job_id: str | None = None,
    payload: dict | None = None,
) -> None:
    """행동 감사 이벤트 1건 기록. 실패해도 호출자 흐름을 막지 않도록 호출부에서 감싼다."""
    now = _utc_now_iso()
    async with _connect() as conn:
        await conn.execute(
            "INSERT INTO events (user_id, event_type, job_id, payload, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, event_type, job_id, json.dumps(payload or {}), now),
        )
        await conn.commit()


async def list_events(limit: int = 100, offset: int = 0) -> list[dict]:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ) as cur:
            rows = await cur.fetchall()
    out: list[dict] = []
    for row in rows:
        d = dict(row)
        d["payload"] = json.loads(d["payload"]) if d["payload"] else {}
        out.append(d)
    return out
