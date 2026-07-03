from __future__ import annotations

import hashlib
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..core import auth as auth_core
from ..core import db
from ..core import email as email_mod
from ..core import oauth as oauth_core
from ..core import ratelimit
from ..core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "session"

# 흔한/유출 비밀번호 차단 — 길이(8자)만으론 'password'·'12345678' 통과(2026-07-03).
# 소규모 큐레이션 리스트(전체 유출DB 아님) — 상위 빈출만. 소문자 비교.
_COMMON_PASSWORDS = frozenset({
    "password", "password1", "password123", "12345678", "123456789", "1234567890",
    "qwerty123", "qwertyuiop", "11111111", "00000000", "iloveyou", "admin123",
    "letmein1", "welcome1", "monkey123", "abc12345", "1q2w3e4r", "zaq12wsx",
    "sunshine1", "princess1", "football1", "baseball1", "trustno1", "passw0rd",
})


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


async def _issue_verification(user_id: int, email: str) -> None:
    """이메일 인증 토큰 발급 + 발송(best-effort). 원문은 링크에만, DB엔 sha256."""
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    await db.create_auth_token(token_hash, user_id, "verify_email", settings.VERIFY_TOKEN_TTL_HOURS)
    base = settings.PUBLIC_BASE_URL or settings.WEB_BASE_URL  # 사용자-대면 URL(내부 렌더 호스트 아님)
    link = f"{base}/verify?token={raw}"
    await email_mod.send_verification_email(email, link)


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
    if body.password.lower() in _COMMON_PASSWORDS:
        raise HTTPException(400, detail={"code": "ERR-AUTH-007", "message": "너무 흔하게 쓰이는 비밀번호입니다. 다른 비밀번호를 사용해 주세요."})
    if await db.get_user_by_email(email) is not None:
        raise HTTPException(400, detail={"code": "ERR-AUTH-003", "message": "이미 사용 중인 이메일입니다."})
    # 오픈 가입 — 초대코드 게이트 폐기(2026-07-02). invites 테이블/헬퍼는 휴면(향후 referral 재활용 가능).
    user_id = await db.create_user(email, auth_core.hash_password(body.password))
    await _start_session(response, user_id)  # grace: 자동로그인 유지, 인증은 비차단
    try:
        await _issue_verification(user_id, email)  # 토큰발급/발송 실패해도 signup 안 깨짐
    except Exception:
        logging.getLogger(__name__).exception("인증메일 발급 실패(비차단) user_id=%s", user_id)
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
            # 부재 이메일도 오답 경로와 대칭으로 429 → 상태코드(401 vs 429) 열거 오라클 차단
            ra = ratelimit.check(ek, settings.LOGIN_EMAIL_LIMIT, settings.LOGIN_EMAIL_WINDOW_S)
            if ra:
                raise ratelimit.too_many(ra)
        raise invalid

    # 비번을 먼저 검증 — 정답은 이메일 실패카운터와 무관하게 항상 통과(피해자 lockout 불가).
    if auth_core.verify_password(user["password_hash"], body.password):
        if rl:
            ratelimit.clear(ek)  # 성공 → 실패카운터 리셋
        if auth_core.needs_rehash(user["password_hash"]):  # argon2 파라미터 상향 시 점진 재해싱
            await db.update_password_hash(user["id"], auth_core.hash_password(body.password))
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
    return {
        "email": user["email"],
        "role": user["role"],
        "emailVerified": bool(user.get("email_verified")),
    }


# ── 이메일 인증 (grace 모드 — 비차단) ──────────────────────────────────────

class ConfirmVerifyBody(BaseModel):
    token: str


@router.post("/request-verify")
async def request_verify(user: dict = Depends(auth_core.get_current_user)):
    """로그인 유저에게 인증메일 재발송 — 유저당 rate limit(쿼터 소진·토큰 증식 방지)."""
    if user.get("email_verified"):
        return {"ok": True, "alreadyVerified": True}
    if settings.RATE_LIMIT_ENABLED:
        k = f"verify:{user['id']}"
        ra = ratelimit.check(k, settings.VERIFY_REQUEST_LIMIT, settings.VERIFY_REQUEST_WINDOW_S)
        if ra:
            raise ratelimit.too_many(ra)
        ratelimit.record(k)
    await _issue_verification(user["id"], user["email"])
    return {"ok": True}


# ── 비밀번호 재설정 (2026-07-03) ───────────────────────────────────────────

class ForgotPasswordBody(BaseModel):
    email: str


class ResetPasswordBody(BaseModel):
    token: str
    password: str


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordBody, request: Request):
    """재설정 메일 요청 — 유저 존재 여부와 무관하게 동일 200 응답(열거 대칭, login 패턴 준수)."""
    email = body.email.strip().lower()
    ip = ratelimit.public_ip(request)
    if settings.RATE_LIMIT_ENABLED and ip is not None:
        for key in (f"reset:ip:{ip}", f"reset:email:{email}"):
            ra = ratelimit.check(key, settings.RESET_REQUEST_LIMIT, settings.RESET_REQUEST_WINDOW_S)
            if ra:
                raise ratelimit.too_many(ra)
            ratelimit.record(key)

    user = await db.get_user_by_email(email)
    # OAuth 전용 유저(빈 해시)는 재설정할 비번이 없음 — 발송 생략, 응답은 동일
    if user is not None and user["password_hash"]:
        try:
            raw = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw.encode()).hexdigest()
            await db.create_auth_token(token_hash, user["id"], "reset_password", settings.RESET_TOKEN_TTL_HOURS)
            base = settings.PUBLIC_BASE_URL or settings.WEB_BASE_URL
            link = f"{base}/reset-password?token={raw}"
            await email_mod.send_reset_email(email, link)
        except Exception:  # 발송 실패도 응답 대칭 유지(존재 오라클 차단)
            logging.getLogger(__name__).exception("재설정 메일 발급 실패 user_id=%s", user["id"])
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordBody):
    """토큰 검증 → 비번 변경 → 전 세션 무효화(탈취 세션 강제 로그아웃). 재로그인 유도."""
    if not 8 <= len(body.password) <= settings.PASSWORD_MAX_LEN:
        raise HTTPException(400, detail={"code": "ERR-AUTH-002", "message": f"비밀번호는 8~{settings.PASSWORD_MAX_LEN}자여야 합니다."})
    if body.password.lower() in _COMMON_PASSWORDS:
        raise HTTPException(400, detail={"code": "ERR-AUTH-007", "message": "너무 흔하게 쓰이는 비밀번호입니다. 다른 비밀번호를 사용해 주세요."})
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    tok = await db.get_auth_token(token_hash, "reset_password")
    if tok is None:
        raise HTTPException(400, detail={"code": "ERR-AUTH-006", "message": "유효하지 않거나 만료된 재설정 링크입니다."})
    await db.update_password_hash(tok["user_id"], auth_core.hash_password(body.password))
    await db.mark_token_used(token_hash)
    await db.delete_sessions_by_user(tok["user_id"])
    await db.log_event("password_reset", user_id=tok["user_id"])
    return {"ok": True}


# ── 소셜 로그인 (Google OAuth, grace — 2026-07-03) ─────────────────────────
OAUTH_STATE_COOKIE = "oauth_state"


def _web_base() -> str:
    """브라우저-대면 프론트 오리진(리다이렉트 목적지)."""
    return (settings.PUBLIC_BASE_URL or settings.WEB_BASE_URL).rstrip("/")


async def _find_or_create_oauth_user(provider: str, sub: str, email: str) -> int:
    """제공자 신원 → users. 순서: 기존 연결 → 동일 이메일 연결 → 신규 생성.
    OAuth 유저는 비번 없음(빈 해시=비번로그인 불가), 제공자가 이메일 검증했으므로 email_verified=1."""
    acct = await db.get_oauth_account(provider, sub)
    if acct:
        return acct["user_id"]
    existing = await db.get_user_by_email(email)
    if existing:
        user_id = existing["id"]
    else:
        user_id = await db.create_user(email, "")   # 빈 해시 → 비번 로그인 불가(소셜 전용)
        await db.set_email_verified(user_id)          # 제공자 검증 이메일 → 인증됨
    await db.link_oauth_account(provider, sub, user_id, email)
    return user_id


@router.get("/oauth/google/start")
async def oauth_google_start():
    """구글 동의화면으로 redirect. 크리덴셜 없으면(dormant) 조용히 /login 복귀."""
    if not oauth_core.google_enabled():
        return RedirectResponse(url=f"{_web_base()}/login?error=oauth_disabled", status_code=302)
    state = secrets.token_urlsafe(24)
    resp = RedirectResponse(url=oauth_core.google_authorize_url(state), status_code=302)
    resp.set_cookie(OAUTH_STATE_COOKIE, state, max_age=600, httponly=True,
                    samesite="lax", secure=settings.COOKIE_SECURE, path="/")  # lax=구글 top-level 복귀 시 전달
    return resp


@router.get("/oauth/google/callback")
async def oauth_google_callback(request: Request, code: str = "", state: str = ""):
    """구글 콜백 → 신원확인 → 세션 발급 → 대시보드. 실패는 /login?error=로 표면화."""
    web = _web_base()
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not code or not state or not cookie_state or state != cookie_state:
        return RedirectResponse(url=f"{web}/login?error=oauth_state", status_code=302)  # CSRF/state 불일치
    try:
        info = await oauth_core.google_exchange(code)
    except Exception:
        logging.getLogger(__name__).exception("google oauth 교환 실패")
        return RedirectResponse(url=f"{web}/login?error=oauth_failed", status_code=302)
    if not info.get("email") or not info.get("email_verified"):
        return RedirectResponse(url=f"{web}/login?error=oauth_no_email", status_code=302)
    user_id = await _find_or_create_oauth_user("google", info["sub"], info["email"])
    resp = RedirectResponse(url=f"{web}/dashboard", status_code=302)
    await _start_session(resp, user_id)
    resp.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    await db.log_event("oauth_login", user_id=user_id, payload={"provider": "google"})
    return resp


@router.post("/confirm-verify")
async def confirm_verify(body: ConfirmVerifyBody):
    """이메일 링크의 토큰 확인 → 인증 완료. 단일사용·TTL."""
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    tok = await db.get_auth_token(token_hash, "verify_email")
    if tok is None:
        raise HTTPException(400, detail={"code": "ERR-AUTH-006", "message": "유효하지 않거나 만료된 인증 링크입니다."})
    await db.set_email_verified(tok["user_id"])
    await db.mark_token_used(token_hash)
    await db.log_event("email_verified", user_id=tok["user_id"])
    return {"ok": True}
