"""소셜 로그인 OAuth 메커니즘 (2026-07-03).

현재 Google만 구현. 크리덴셜(.env) 비면 dormant.
authorize URL 생성 + code→token→userinfo 교환. find/link/create 로직은 라우터가 담당.
카카오는 아직 미구현(프론트 '준비중' 버튼) — 비즈앱 심사 후 추가.
"""
from __future__ import annotations

from urllib.parse import urlencode

import httpx

from .config import settings

_GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"


def redirect_uri(provider: str) -> str:
    """제공자에 등록할 콜백 URL. 브라우저-대면 프론트 오리진 기준(dev=localhost:3000).
    Next rewrite가 /api를 백엔드로 프록시하므로 세션쿠키가 앱과 동일 오리진에 실림."""
    base = settings.OAUTH_REDIRECT_BASE or settings.PUBLIC_BASE_URL or settings.WEB_BASE_URL
    return f"{base.rstrip('/')}/api/auth/oauth/{provider}/callback"


def google_enabled() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def google_authorize_url(state: str) -> str:
    q = urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri("google"),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    })
    return f"{_GOOGLE_AUTH}?{q}"


async def google_exchange(code: str) -> dict:
    """code → access_token → userinfo. 반환 {sub, email, email_verified, name}. 실패 시 예외."""
    async with httpx.AsyncClient(timeout=10) as client:
        tok = await client.post(_GOOGLE_TOKEN, data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri("google"),
        })
        tok.raise_for_status()
        access = tok.json()["access_token"]
        ui = await client.get(_GOOGLE_USERINFO, headers={"Authorization": f"Bearer {access}"})
        ui.raise_for_status()
        d = ui.json()
    return {
        "sub": d["sub"],
        "email": (d.get("email") or "").strip().lower(),
        "email_verified": bool(d.get("email_verified")),
        "name": d.get("name"),
    }


# ── 인스타 발행 연동 (Instagram Login, 2026-07-23) ──────────────────────────
# graph.instagram.com. FB 페이지 불필요. 스코프·엔드포인트는 Meta 최신문서 대조 완료(2026-07-23).
_IG_AUTH = "https://www.instagram.com/oauth/authorize"
_IG_TOKEN = "https://api.instagram.com/oauth/access_token"
_IG_GRAPH = "https://graph.instagram.com"
_IG_SCOPES = "instagram_business_basic,instagram_business_content_publish"


def instagram_enabled() -> bool:
    return bool(settings.INSTAGRAM_CLIENT_ID and settings.INSTAGRAM_CLIENT_SECRET)


def instagram_authorize_url(state: str) -> str:
    q = urlencode({
        "client_id": settings.INSTAGRAM_CLIENT_ID,
        "redirect_uri": redirect_uri("instagram"),
        "response_type": "code",
        "scope": _IG_SCOPES,
        "state": state,
    })
    return f"{_IG_AUTH}?{q}"


async def instagram_exchange(code: str) -> dict:
    """code → short-lived → long-lived(60d) → username. 반환:
    {ig_user_id, access_token(long), expires_in, ig_username}. 실패 시 예외.
    ★M1: /me GET은 토큰을 Bearer 헤더로 실어 URL·로그 유출 방지(google_exchange 패턴)."""
    async with httpx.AsyncClient(timeout=15) as client:
        tok = await client.post(_IG_TOKEN, data={
            "client_id": settings.INSTAGRAM_CLIENT_ID,
            "client_secret": settings.INSTAGRAM_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri("instagram"),
            "code": code,
        })
        tok.raise_for_status()
        short = tok.json()
        ig_user_id = str(short["user_id"])
        ll = await client.get(f"{_IG_GRAPH}/access_token", params={
            "grant_type": "ig_exchange_token",
            "client_secret": settings.INSTAGRAM_CLIENT_SECRET,
            "access_token": short["access_token"],
        })
        ll.raise_for_status()
        long_tok = ll.json()
        me = await client.get(
            f"{_IG_GRAPH}/me",
            params={"fields": "user_id,username"},
            headers={"Authorization": f"Bearer {long_tok['access_token']}"},
        )
        me.raise_for_status()
        prof = me.json()
    return {
        "ig_user_id": ig_user_id,
        "access_token": long_tok["access_token"],
        "expires_in": long_tok.get("expires_in"),
        "ig_username": prof.get("username"),
    }
