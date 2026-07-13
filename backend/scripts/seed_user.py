"""계정 시드 — 운영자가 계정을 미리 만들고 이메일 인증까지 처리(파일럿용).

이메일 발송(Resend)이 테스트모드라 외부 사용자 인증메일이 안 갈 때, 운영자가 직접
계정을 만들어 email_verified=1로 세팅한다(업로드 grace 상한 해제, 로그인 즉시 가능).

사용법: python -m backend.scripts.seed_user <email> <password> [role]
  - 새 이메일  → 생성 + 이메일 인증
  - 이미 가입  → 이메일 인증만 처리(비밀번호 인자는 무시, 아무거나 넣어도 됨)
  role 생략 시 'user'. 관리자는 'admin'.
"""
from __future__ import annotations

import asyncio
import sys

from backend.core import db
from backend.core.auth import hash_password


async def main(email: str, password: str, role: str = "user") -> None:
    email = email.strip().lower()  # 로그인 경로와 정규화 일치(대소문자 불일치 잠금 방지)
    await db.migrate()
    existing = await db.get_user_by_email(email)
    if existing is not None:
        await db.set_email_verified(existing["id"])
        print(f"이미 존재 → 이메일 인증 처리: id={existing['id']} email={email} (비밀번호 미변경)")
        return
    uid = await db.create_user(email, hash_password(password), role=role)
    await db.set_email_verified(uid)
    print(f"생성 + 이메일 인증됨: id={uid} email={email} role={role}")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print("사용법: python -m backend.scripts.seed_user <email> <password> [role]")
        sys.exit(1)
    role = sys.argv[3] if len(sys.argv) == 4 else "user"
    asyncio.run(main(sys.argv[1], sys.argv[2], role))
