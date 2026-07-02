"""계정 시드.

사용법: python -m backend.scripts.seed_user <email> <password> [role]
  role 생략 시 'user'. 관리자는 'admin'.
"""
from __future__ import annotations

import asyncio
import sys

from backend.core import db
from backend.core.auth import hash_password


async def main(email: str, password: str, role: str = "user") -> None:
    await db.migrate()
    if await db.get_user_by_email(email) is not None:
        print(f"이미 존재: {email}")
        return
    uid = await db.create_user(email, hash_password(password), role=role)
    print(f"생성됨: id={uid} email={email} role={role}")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print("사용법: python -m backend.scripts.seed_user <email> <password> [role]")
        sys.exit(1)
    role = sys.argv[3] if len(sys.argv) == 4 else "user"
    asyncio.run(main(sys.argv[1], sys.argv[2], role))
