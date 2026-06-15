"""박사님 계정 시드.

사용법: python -m backend.scripts.seed_user <email> <password>
"""
from __future__ import annotations

import asyncio
import sys

from backend.core import db
from backend.core.auth import hash_password


async def main(email: str, password: str) -> None:
    await db.migrate()
    if await db.get_user_by_email(email) is not None:
        print(f"이미 존재: {email}")
        return
    uid = await db.create_user(email, hash_password(password), role="user")
    print(f"생성됨: id={uid} email={email}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python -m backend.scripts.seed_user <email> <password>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
