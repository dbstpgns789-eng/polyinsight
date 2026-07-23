"""소셜 토큰 대칭 암호화 (2026-07-23). IG 토큰은 발행 때 되돌려 써야 해 단방향 해시 불가.
키(SOCIAL_TOKEN_KEY) 없으면 dormant — 호출 전 enabled()로 가드."""
from __future__ import annotations

from cryptography.fernet import Fernet

from .config import settings


def enabled() -> bool:
    return bool(settings.SOCIAL_TOKEN_KEY)


def _fernet() -> Fernet:
    return Fernet(settings.SOCIAL_TOKEN_KEY.encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
