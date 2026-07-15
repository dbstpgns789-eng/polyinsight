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
