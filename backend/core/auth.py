from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import HTTPException, Request

from . import db
from .config import settings

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        _ph.verify(password_hash, password)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


_UNAUTH = HTTPException(
    status_code=401,
    detail={"code": "ERR-AUTH-001", "message": "인증이 필요합니다."},
)


async def get_current_user(request: Request) -> dict:
    # 내부 렌더 서비스(Playwright) 우회: 유효한 X-Render-Token이면 서비스 사용자로 통과
    rt = request.headers.get("x-render-token")
    if settings.RENDER_TOKEN and rt == settings.RENDER_TOKEN:
        return {"id": 0, "email": "__render__", "role": "service"}

    token = request.cookies.get("session")
    if not token:
        raise _UNAUTH
    sess = await db.get_valid_session(token)
    if sess is None:
        raise _UNAUTH
    user = await db.get_user_by_id(sess["user_id"])
    if user is None:
        raise _UNAUTH
    return user
