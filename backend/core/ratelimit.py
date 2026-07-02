"""인메모리 슬라이딩 윈도우 rate limiter (무의존).

단일 uvicorn 워커 전제 — 단일 이벤트루프 스레드라 dict/deque 연산이 원자적(await 없음).
멀티워커로 가면 SQLite/Redis 백엔드로 교체 필요. 프로세스 재시작 시 카운터 초기화(공격자가
재시작을 유발 못하므로 보안 구멍 아님). 브루트포스 경로에 DB 쓰기를 피하는 게 핵심.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_hits: dict[str, deque[float]] = defaultdict(deque)


def check(key: str, limit: int, window: float) -> int | None:
    """window(초) 내 key 히트가 limit 이상이면 retry_after(초)를, 아니면 None. 기록/삽입 안 함.
    미존재 키는 .get으로 조회만(빈 deque 삽입 금지 — 무한증식 방지)."""
    dq = _hits.get(key)
    if not dq:
        return None
    now = time.monotonic()
    cutoff = now - window
    while dq and dq[0] <= cutoff:
        dq.popleft()
    if len(dq) >= limit:
        return int(window - (now - dq[0])) + 1
    return None


def record(key: str) -> None:
    _hits[key].append(time.monotonic())


def clear(key: str) -> None:
    _hits.pop(key, None)


def sweep(max_window: float = 3600.0) -> int:
    """max_window보다 오래된 항목 제거 + 빈 deque 키 회수. _ttl_cleaner가 주기 호출."""
    now = time.monotonic()
    cutoff = now - max_window
    dropped = 0
    for key in list(_hits.keys()):
        dq = _hits[key]
        while dq and dq[0] <= cutoff:
            dq.popleft()
        if not dq:
            del _hits[key]
            dropped += 1
    return dropped


def reset_all() -> None:
    """테스트 격리용."""
    _hits.clear()


def public_ip(request: Request) -> str | None:
    """공개 엣지(Cloudflare)가 세팅한 신뢰 가능한 클라이언트 IP. 없으면 None.
    cloudflared는 엣지에서 cf-connecting-ip를 항상 덮어씀(클라 위조 불가). 이 헤더가 없으면
    = 내부/로컬/프록시 경로 → rate limit 미적용(dev 자동 면제). X-Forwarded-For는 위조 가능해 신뢰 안 함.
    (프로덕션: Next rewrite가 이 헤더를 백엔드로 전달해야 함 — 기본 전달됨.)"""
    cf = request.headers.get("cf-connecting-ip")
    return cf.strip() if cf else None


def too_many(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={"code": "ERR-AUTH-429", "message": "너무 많은 시도입니다. 잠시 후 다시 시도해 주세요."},
        headers={"Retry-After": str(retry_after)},
    )
