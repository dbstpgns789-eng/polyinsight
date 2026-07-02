"""유저별 격리 마이그레이션 — 기존(무소유) 잡을 admin에 귀속 + 테스트 계정 정리.

사용법:
  python -m backend.scripts.migrate_ownership <admin_email> [--purge a@x,b@y,...]

- migrate()로 jobs.user_id 컬럼 보장(idempotent)
- user_id IS NULL 인 기존 잡 전부 admin에 귀속(카드 데이터 무손실, 소유자 표기만)
- --purge 이메일들: 세션 삭제 + invites.used_by 해제 후 계정 삭제
"""
from __future__ import annotations

import asyncio
import sys

import aiosqlite

from backend.core import db


async def main(admin_email: str, purge_emails: list[str]) -> None:
    await db.migrate()
    admin = await db.get_user_by_email(admin_email)
    if admin is None:
        print(f"admin 없음: {admin_email} — 중단")
        return
    path = db._db_path()
    async with aiosqlite.connect(path) as conn:
        cur = await conn.execute(
            "UPDATE jobs SET user_id = ? WHERE user_id IS NULL", (admin["id"],)
        )
        await conn.commit()
        print(f"backfill: {cur.rowcount} jobs -> admin(id={admin['id']}, {admin_email})")

        for email in purge_emails:
            u = await db.get_user_by_email(email)
            if u is None:
                print(f"  purge skip(없음): {email}")
                continue
            if u["id"] == admin["id"]:
                print(f"  purge skip(admin 보호): {email}")
                continue
            await conn.execute("DELETE FROM sessions WHERE user_id = ?", (u["id"],))
            await conn.execute("UPDATE invites SET used_by = NULL WHERE used_by = ?", (u["id"],))
            await conn.execute("DELETE FROM users WHERE id = ?", (u["id"],))
            await conn.commit()
            print(f"  purge: {email} (id={u['id']})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python -m backend.scripts.migrate_ownership <admin_email> [--purge a@x,b@y]")
        sys.exit(1)
    admin_email = sys.argv[1]
    purge: list[str] = []
    if "--purge" in sys.argv:
        purge = [e.strip() for e in sys.argv[sys.argv.index("--purge") + 1].split(",") if e.strip()]
    asyncio.run(main(admin_email, purge))
