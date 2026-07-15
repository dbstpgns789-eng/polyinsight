"""demo 유저 + 세션 토큰 시드. 토큰을 stdout에 출력(Playwright 쿠키용)."""
import os
import sys
import uuid
import asyncio

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = os.path.join(REPO, "backend", "polyinsight.db")
sys.path.insert(0, REPO)


async def main():
    from backend.core import db
    from backend.core.auth import hash_password
    await db.migrate()
    email = "demo@poly.test"
    user = await db.get_user_by_email(email)
    if user is None:
        uid = await db.create_user(email, hash_password("demo1234"), role="user")
    else:
        uid = user["id"]
    token = uuid.uuid4().hex
    await db.create_session(token, uid, ttl_hours=72)
    print(token)


if __name__ == "__main__":
    asyncio.run(main())
