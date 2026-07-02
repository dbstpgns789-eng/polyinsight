from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import HTTPException, Request

from . import db
from .config import settings

_ph = PasswordHasher()

# 로그인 타이밍/열거 오라클 방지 — 유저 부재 시에도 argon2 1회 실행해 응답시간 균등화.
_DUMMY_HASH = _ph.hash("timing-equalization-dummy")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_dummy() -> None:
    """존재하지 않는 유저 로그인 경로에서 호출 — 실제 verify와 동일한 argon2 비용 발생."""
    try:
        _ph.verify(_DUMMY_HASH, "x")
    except Exception:
        pass


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


async def require_owned_job(job_id: str, user: dict) -> dict:
    """job 로드 + 소유권 검사. 내부 렌더 서비스(role=service)는 우회.
    소유자 아니면 404(존재 자체를 은닉 — IDOR 방어). 반환=job dict(재사용)."""
    job = await db.get_job(job_id)
    _NOT_FOUND = HTTPException(
        status_code=404,
        detail={"code": "ERR-JOB-001", "message": "프로젝트를 찾을 수 없습니다."},
    )
    if job is None:
        raise _NOT_FOUND
    if user.get("role") == "service":
        return job
    if job.get("user_id") != user.get("id"):
        raise _NOT_FOUND
    return job


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
