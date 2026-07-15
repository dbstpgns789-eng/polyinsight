"""이메일 발송 (Resend HTTP API).

SMTP가 아니라 HTTPS API — Oracle ARM/CF 터널에서 아웃바운드 SMTP(25/587)가 막혀도 동작.
RESEND_API_KEY 비면 no-op(dormant). 발송 실패는 절대 호출자 흐름을 막지 않는다(로그+False).
"""
from __future__ import annotations

import logging

import httpx

from .config import settings

log = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


def _verify_html(link: str) -> str:
    return (
        '<div style="font-family:sans-serif;max-width:480px;margin:0 auto;color:#1a1a1a">'
        '<h2 style="font-weight:700">PolyInsight 이메일 인증</h2>'
        '<p>아래 버튼을 눌러 이메일을 인증해 주세요. 링크는 24시간 후 만료됩니다.</p>'
        f'<p><a href="{link}" style="display:inline-block;background:#0b8a67;color:#fff;'
        'text-decoration:none;padding:12px 22px;border-radius:10px;font-weight:600">이메일 인증</a></p>'
        f'<p style="font-size:12px;color:#666">버튼이 안 되면 이 주소를 붙여넣으세요:<br>{link}</p>'
        '</div>'
    )


async def _send(to: str, subject: str, html: str) -> bool:
    if not settings.RESEND_API_KEY:
        log.info("RESEND_API_KEY 미설정 — 이메일 발송 skip (to=%s)", to)
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={
                    "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
        if r.status_code >= 400:
            log.error("Resend 발송 실패 %s: %s", r.status_code, r.text[:200])
            return False
        return True
    except Exception as exc:  # 네트워크/타임아웃 — 흐름 차단 금지
        log.error("Resend 발송 예외: %s", exc)
        return False


async def send_verification_email(to: str, link: str) -> bool:
    return await _send(to, "PolyInsight 이메일 인증", _verify_html(link))


def _reset_html(link: str) -> str:
    return (
        '<div style="font-family:sans-serif;max-width:480px;margin:0 auto;color:#1a1a1a">'
        '<h2 style="font-weight:700">PolyInsight 비밀번호 재설정</h2>'
        '<p>아래 버튼을 눌러 새 비밀번호를 설정해 주세요. 링크는 2시간 후 만료됩니다.</p>'
        '<p>요청하지 않으셨다면 이 메일을 무시하세요 — 비밀번호는 바뀌지 않습니다.</p>'
        f'<p><a href="{link}" style="display:inline-block;background:#0b8a67;color:#fff;'
        'text-decoration:none;padding:12px 22px;border-radius:10px;font-weight:600">비밀번호 재설정</a></p>'
        f'<p style="font-size:12px;color:#666">버튼이 안 되면 이 주소를 붙여넣으세요:<br>{link}</p>'
        '</div>'
    )


async def send_reset_email(to: str, link: str) -> bool:
    return await _send(to, "PolyInsight 비밀번호 재설정", _reset_html(link))
