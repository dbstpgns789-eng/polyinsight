"""플랜 게이트 — 무료체험(export-gate 순수잠금)의 판정 단일 소스.

무료 = 1덱 "보기 전용". 생성·뷰어·직접 편집(PATCH)·검증 배지는 열려 있고(아하),
파일이 나가는 export와 LLM 원가가 드는 AI 디자이너(자연어 편집)만 잠근다.
벽은 세 겹이고 역할이 다르다:
  - export 게이트        = 가치 벽 (WTP가 최고조인 지점)
  - 생성 1회 상한        = 원가 방어 (덱 1건 ≈ $1)
  - AI 디자이너 게이트   = 원가 방어 (자연어 편집 호출마다 LLM)

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


def should_consume_free_deck(user: dict) -> bool:
    """무료 체험 카운터를 소비해야 하는 유저인가 — 서비스 롤·유료는 제외.

    can_author/can_export와 같은 면제 규칙(_is_exempt)을 재사용한다. 호출부가
    plan_of()만 보고 이 규칙을 다시 구현하면, plan 키가 없는 서비스 유저
    (X-Render-Token, {"id","email","role"} 3키뿐)가 "free"로 폴백돼 원자적
    소비 블록에서 잘못 402를 맞는다 — 이 함수가 그 불변식을 한 곳에 모은다.
    """
    return not _is_exempt(user) and plan_of(user) not in PAID_PLANS


class PlanGateError(HTTPException):
    """플랜 벽. user_id를 실어 보내 main.py의 예외 핸들러가 벽 히트 이벤트를 남긴다.

    request.state에 유저를 심지 않기 때문에 예외가 직접 들고 간다.
    """

    def __init__(self, gate_kind: str, code: str, message: str, user_id: int | None = None):
        super().__init__(status_code=402, detail={"code": code, "message": message})
        self.gate_kind = gate_kind
        self.user_id = user_id


def author_gate_error(user: dict | None = None) -> PlanGateError:
    """생성 게이트 402. 읽기 판정(require_can_author)과 원자적 소비 실패가
    같은 응답을 내야 프론트가 한 가지 분기만 다루면 된다."""
    return PlanGateError(
        gate_kind="author",
        code="ERR-PLAN-AUTHOR",
        message="무료 체험 1덱을 모두 사용했어요. 업그레이드하면 계속 만들 수 있어요.",
        user_id=(user or {}).get("id"),
    )


def export_gate_error(user: dict | None = None) -> PlanGateError:
    return PlanGateError(
        gate_kind="export",
        code="ERR-PLAN-EXPORT",
        message="내보내기는 업그레이드 후 이용할 수 있어요. 만든 카드뉴스는 그대로 보관돼요.",
        user_id=(user or {}).get("id"),
    )


def require_can_author(user: dict) -> None:
    if not can_author(user):
        raise author_gate_error(user)


def require_can_export(user: dict) -> None:
    if not can_export(user):
        raise export_gate_error(user)


def can_use_ai_designer(user: dict) -> bool:
    """AI 디자이너(자연어 편집)를 쓸 수 있나 — 유료(pro/lab)만.

    자연어 편집(nlpatch·propose)은 호출마다 LLM 원가가 발생한다. 무료가 이걸
    무제한 쓰면 지출이 샌다(export 벽과 같은 원리 — 무료가 무한히 태우는 지출 차단).
    직접 편집(PATCH)은 LLM을 안 써 무료로 열어 둔다. 판정은 can_export와 같지만
    (유료만) gate_kind/code가 달라 벽 히트가 분류되고 프론트가 별도 메시지를 그린다.
    """
    if _is_exempt(user):
        return True
    return plan_of(user) in PAID_PLANS


def ai_designer_gate_error(user: dict | None = None) -> PlanGateError:
    return PlanGateError(
        gate_kind="ai_designer",
        code="ERR-PLAN-AI-DESIGNER",
        message="AI 디자이너는 업그레이드 후 이용할 수 있어요. 직접 편집은 무료로 계속 쓸 수 있어요.",
        user_id=(user or {}).get("id"),
    )


def require_can_ai_designer(user: dict) -> None:
    if not can_use_ai_designer(user):
        raise ai_designer_gate_error(user)
