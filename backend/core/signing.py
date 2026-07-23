"""공개 카드 URL HMAC 서명 (2026-07-23). Meta가 쿠키 없이 카드 이미지를 긁게 하되,
서명+만료로 무제한 노출 방지. 발행 순간에만 소유자에게 발급.
★M3: 시크릿 비면 dormant — verify는 무조건 False(빈키 HMAC=공개키 위조 차단)."""
from __future__ import annotations

import hashlib
import hmac
import time

from .config import settings


def enabled() -> bool:
    return len(settings.PUBLIC_CARD_URL_SECRET or "") >= 16


def _mac(job_id: str, card_num: int, exp: int) -> str:
    msg = f"{job_id}:{card_num}:{exp}".encode()
    return hmac.new(settings.PUBLIC_CARD_URL_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def sign_card(job_id: str, card_num: int, ttl_s: int = 600) -> tuple[int, str]:
    exp = int(time.time()) + ttl_s
    return exp, _mac(job_id, card_num, exp)


def verify_card(job_id: str, card_num: int, exp: int, sig: str) -> bool:
    if not enabled():                 # M3: 시크릿 없으면 무조건 거부(빈키 위조 차단)
        return False
    if exp < int(time.time()):
        return False
    return hmac.compare_digest(_mac(job_id, card_num, exp), sig)
