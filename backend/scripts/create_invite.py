"""초대코드 1개 생성 후 출력.

사용법: python -m backend.scripts.create_invite
"""
from __future__ import annotations

import asyncio
import secrets

from backend.core import db


async def main() -> None:
    await db.migrate()
    code = secrets.token_urlsafe(8)
    await db.create_invite(code)
    print(f"초대코드: {code}")


if __name__ == "__main__":
    asyncio.run(main())
