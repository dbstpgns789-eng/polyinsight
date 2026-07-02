from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ..core import auth as auth_core
from ..core import db
from ..core import ratelimit
from ..core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "session"


class SignupBody(BaseModel):
    email: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        path="/",
    )


async def _start_session(response: Response, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    await db.create_session(token, user_id, settings.SESSION_TTL_HOURS)
    _set_session_cookie(response, token)
    return token


@router.post("/signup")
async def signup(body: SignupBody, request: Request, response: Response):
    email = body.email.strip().lower()
    ip = ratelimit.public_ip(request)  # CF 엣지 IP만 신뢰. 없으면(dev/내부) rate limit 면제.
    if settings.RATE_LIMIT_ENABLED and ip is not None:
        ra = ratelimit.check(f"signup:ip:{ip}", settings.SIGNUP_IP_LIMIT, settings.SIGNUP_IP_WINDOW_S)
        if ra:
            raise ratelimit.too_many(ra)
        ratelimit.record(f"signup:ip:{ip}")
    if not 8 <= len(body.password) <= settings.PASSWORD_MAX_LEN:
        raise HTTPException(400, detail={"code": "ERR-AUTH-002", "message": f"비밀번호는 8~{settings.PASSWORD_MAX_LEN}자여야 합니다."})
    if await db.get_user_by_email(email) is not None:
        raise HTTPException(400, detail={"code": "ERR-AUTH-003", "message": "이미 사용 중인 이메일입니다."})
    # 오픈 가입 — 초대코드 게이트 폐기(2026-07-02). invites 테이블/헬퍼는 휴면(향후 referral 재활용 가능).
    user_id = await db.create_user(email, auth_core.hash_password(body.password))
    await _start_session(response, user_id)
    await db.log_event("signup", user_id=user_id)  # PII(email) 미기록 — user_id로 연결
    return {"email": email}


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response):
    email = body.email.strip().lower()
    invalid = HTTPException(401, detail={"code": "ERR-AUTH-005", "message": "이메일 또는 비밀번호가 올바르지 않습니다."})
    ip = ratelimit.public_ip(request)  # CF 엣지 IP만. 없으면(dev/내부) 면제.
    rl = settings.RATE_LIMIT_ENABLED and ip is not None
    ek = f"login:email:{email}"

    # IP 한도는 사전 차단(공격자 IP 기준 상한 — 모든 시도 카운트).
    if rl:
        ipk = f"login:ip:{ip}"
        ra = ratelimit.check(ipk, settings.LOGIN_IP_LIMIT, settings.LOGIN_IP_WINDOW_S)
        if ra:
            raise ratelimit.too_many(ra)
        ratelimit.record(ipk)

    # argon2 pre-hash DoS 상한 — 로그인에도 적용(존재 은닉 위해 동일 401).
    if len(body.password) > settings.PASSWORD_MAX_LEN:
        raise invalid

    user = await db.get_user_by_email(email)
    if user is None:
        auth_core.verify_dummy()  # 타이밍/열거 오라클 방지 — 부재 시에도 argon2 1회
        if rl:
            ratelimit.record(ek)
        raise invalid

    # 비번을 먼저 검증 — 정답은 이메일 실패카운터와 무관하게 항상 통과(피해자 lockout 불가).
    if auth_core.verify_password(user["password_hash"], body.password):
        if rl:
            ratelimit.clear(ek)  # 성공 → 실패카운터 리셋
        await _start_session(response, user["id"])
        await db.log_event("login", user_id=user["id"])
        return {"email": user["email"]}

    # 오답만: 이메일 카운터 누적 → 한도 초과 시 오답 응답을 429로(정답은 위에서 이미 통과).
    if rl:
        ratelimit.record(ek)
        ra = ratelimit.check(ek, settings.LOGIN_EMAIL_LIMIT, settings.LOGIN_EMAIL_WINDOW_S)
        if ra:
            raise ratelimit.too_many(ra)
    raise invalid


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        sess = await db.get_valid_session(token)
        await db.delete_session(token)
        if sess:
            await db.log_event("logout", user_id=sess["user_id"])
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(auth_core.get_current_user)):
    return {"email": user["email"], "role": user["role"]}
