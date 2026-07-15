"""Resend 발송 격리 테스트 — 풀 가입 플로우 없이 '메일 발송 되나'만 확인.

사용법: python -m backend.scripts.test_email <to@email> [link]
- RESEND_API_KEY(.env)가 있어야 실제 발송. 비면 no-op(skip).
- onboarding@resend.dev(기본 EMAIL_FROM)은 도메인 DKIM 검증 전엔
  '너의 Resend 계정 이메일'로만 배달됨 → <to>를 그 주소로.
"""
from __future__ import annotations

import asyncio
import sys

from backend.core import email as email_mod
from backend.core.config import settings


async def main(to: str, link: str) -> None:
    key = "set" if settings.RESEND_API_KEY else "EMPTY(no-op)"
    print(f"from={settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>  RESEND_API_KEY={key}")
    ok = await email_mod.send_verification_email(to, link)
    print("발송 결과:", "성공 ✓ (메일함 확인)" if ok else "실패/skip — 위 from/key + run.log 확인")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python -m backend.scripts.test_email <to@email> [link]")
        sys.exit(1)
    target = sys.argv[1]
    verify_link = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3000/verify?token=TEST"
    asyncio.run(main(target, verify_link))
