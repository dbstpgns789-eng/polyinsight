"""플랜 게이트 — 무료체험(export-gate 순수잠금)의 판정 단일 소스.

무료 = 1덱 "보기 전용". 생성·뷰어·편집·검증 배지는 전부 열려 있고(아하),
파일이 실제로 나가는 export 경로만 잠근다. 벽은 두 겹이고 역할이 다르다:
  - export 게이트   = 가치 벽 (WTP가 최고조인 지점)
  - 생성 1회 상한   = 원가 방어 (덱 1건 ≈ $1)

주의: 유저 dict는 항상 DB row라고 가정하지 않는다. X-Render-Token 서비스 유저
(backend/core/auth.py:71)는 {"id","email","role"} 3키뿐이라 plan 키가 없다.
전부 .get()으로 읽고, 서비스 롤은 게이트 면제다.
"""
from __future__ import annotations

from fastapi import HTTPException

FREE_DECK_LIMIT = 1
PAID_PLANS = ("pro", "lab")


def _is_exempt(user: dict) -> bool:
    """내부 렌더 서비스 — 게이트 대상 아님."""
    return user.get("role") == "service"


def plan_of(user: dict) -> str:
    return user.get("plan") or "free"


def free_decks_used(user: dict) -> int:
    return int(user.get("free_decks_used") or 0)


def can_author(user: dict) -> bool:
    """새 덱을 만들 수 있나 — 무료는 평생 FREE_DECK_LIMIT회."""
    if _is_exempt(user) or plan_of(user) in PAID_PLANS:
        return True
    return free_decks_used(user) < FREE_DECK_LIMIT


def can_export(user: dict) -> bool:
    """파일로 내보낼 수 있나 — 무료는 절대 불가(순수잠금, 워터마크 타협 없음)."""
    if _is_exempt(user):
        return True
    return plan_of(user) in PAID_PLANS


def author_gate_error() -> HTTPException:
    """생성 게이트 402. 읽기 판정(require_can_author)과 원자적 소비 실패가
    같은 응답을 내야 프론트가 한 가지 분기만 다루면 된다."""
    return HTTPException(
        status_code=402,
        detail={
            "code": "ERR-PLAN-AUTHOR",
            "message": "무료 체험 1덱을 모두 사용했어요. 업그레이드하면 계속 만들 수 있어요.",
        },
    )


def export_gate_error() -> HTTPException:
    return HTTPException(
        status_code=402,
        detail={
            "code": "ERR-PLAN-EXPORT",
            "message": "내보내기는 업그레이드 후 이용할 수 있어요. 만든 카드뉴스는 그대로 보관돼요.",
        },
    )


def require_can_author(user: dict) -> None:
    if not can_author(user):
        raise author_gate_error()


def require_can_export(user: dict) -> None:
    if not can_export(user):
        raise export_gate_error()
