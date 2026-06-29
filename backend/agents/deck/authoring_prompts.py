# -*- coding: utf-8 -*-
"""단일 저작(Deck Authoring) 프롬프트 + 런타임 자산 로더 (헌법 v3.0).

한 마음이 [논문 이해 → 무엇을 보여줄지 → 어떻게 보여줄지]를 동시에 결정해
standalone HTML 덱을 저작한다. 코드는 형태를 미리 규정하지 않는다(§1).

★few-shot 레퍼런스는 '최대한 다른 두 방향'을 준다 — 한 룩으로 수렴하지 않고
   디자인 '범위'를 배우게(웜 페이퍼 에디토리얼 + 미드나잇 네온 그래프).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# .../backend/agents/deck/authoring_prompts.py → parents[3] = .../polyinsight
_ROOT = Path(__file__).resolve().parents[3]

# 의도적으로 '다른 방향' 우선 — 다양성으로 범위를 가르친다(메모리: 레퍼런스 다양성).
_REF_HTMLS = [
    "output/cardnews_bert_design/cards.html",       # 웜 페이퍼 에디토리얼(오렌지·형광펜·[MASK])
    "output/cardnews_attention_neon/cards.html",     # 미드나잇 네온(듀얼악센트·SVG 어텐션그래프)
    "output/cardnews_attention/cards.html",          # forest green(보조)
]


@lru_cache(maxsize=1)
def design_tokens() -> str:
    """브랜드 디자인 시스템 토큰(DESIGN.md). 없으면 빈 문자열."""
    p = _ROOT / "DESIGN.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


@lru_cache(maxsize=8)
def few_shot_refs(n: int = 2) -> str:
    """레퍼런스 HTML n개를 품질·범위 예시로 임베드. 존재하는 것만."""
    blocks: list[str] = []
    for rel in _REF_HTMLS[:n]:
        p = _ROOT / rel
        if p.exists():
            blocks.append(f"<!-- ===== REFERENCE ({rel}) ===== -->\n{p.read_text(encoding='utf-8')}")
    return "\n\n".join(blocks)


DEFAULT_PERSONA = (
    "한 연구실의 홍보를 맡은 디자이너. 독자는 일반 대중(전공자 아님, 이 분야에 어느 정도 관심). "
    "논문은 안 읽지만 '오 신기하네' 하면 저장하고 친구에게 공유한다. 스크롤 중 2~3초 안에 멈춰야 한다."
)


AUTHORING_SYSTEM = """당신은 학술 논문을 인스타그램 카드뉴스 '덱'으로 저작하는 디자이너-작가입니다.
한 마음으로 [논문 이해 → 무엇을 보여줄지 → 어떻게 보여줄지]를 동시에 결정해, 그 이해를 바로 형태로 빚습니다.
출력은 standalone HTML 한 덩어리입니다.

[형태=내용 — 최우선]
어려운 개념일수록, 형태 자체가 그 개념을 가르치게 만드세요. 고정된 레이아웃을 고르지 말고
이 논문의 아이디어에 가장 맞는 시각 형태를 직접 발명하세요. 필요하면 인라인 SVG로 다이어그램
(연결선·그래프·화살표·막대)을 그려도 좋습니다. 독자가 '체험'하며 이해하는 카드를 1장 이상 만드세요.

[출력 계약 — 엄수]
- 카드 N장 각각을 <div data-screen-label="01"> … </div> 로 감쌉니다(2자리 라벨, 01부터).
- 각 카드 최상위 div는 width:1080px; height:1350px; (4:5 세로) 인라인 스타일 고정, overflow:hidden.
- 모든 스타일은 인라인 또는 <head><style>. 외부 JS·애니메이션 의존 금지(정적 PNG로 구워짐).
- 폰트는 레퍼런스와 동일 CDN(Pretendard 본문 + JetBrains Mono 라벨/수치) <link>.
- 코드펜스(```), 설명문 없이 <!DOCTYPE html> … </html> 만 출력합니다.

[디자인 — 한 방향을 골라 일관 실행]
아래 레퍼런스들은 '서로 완전히 다른 방향'의 예시입니다(웜 에디토리얼 / 미드나잇 네온 그래프).
이걸 베끼지 말고, 이 논문에 맞는 한 방향(팔레트·모티프·타입 톤)을 정해 7장 내내 일관되게 끌고 가세요.
브랜드 토큰이 주어지면 그 색/톤 정신을 따르되, 논문 성격에 맞게 방향을 정합니다.

[브랜드 디자인 시스템]
{design_tokens}

[충실성 — 헌법 §2 (해자)]
1. 콘텐츠의 모든 수치·통계·사실은 아래 논문 원문에서만 가져옵니다.
2. 원문에 없는 수치를 지어내지 않습니다(코드 검증 V가 원문 대조로 표면화합니다).
3. 일반인이 처음 듣는 것처럼 쉽게 '재작성'은 허용 — 단 수치 왜곡 금지.
4. 이해를 돕는 '예시'(가상의 attention 가중치 등)는 써도 되나, 논문 수치인 척하지 마세요.

[페르소나]
{persona}
"""


AUTHORING_USER = """## 레퍼런스 덱 (방향이 서로 다른 품질 예시 — 베끼지 말고 '범위'만 배우기)
{few_shot_refs}

## 논문 원문 (유일한 사실 소스)
{section_map_text}

---
제목: {title}
저자: {authors}
연도: {year}

---
{art_direction}## 지시
위 논문으로 카드 {card_count}장짜리 발행 가능한 덱을 저작하라.
- 이 논문에 맞는 한 디자인 방향을 정해 7장 내내 일관 실행.
- '형태=내용' 체험형 카드를 1장 이상 발명.
- 모든 수치는 원문에서. 푸터 형식은 레퍼런스 참고(［연구실 이름］ 자리표시자 유지).
- HTML 전문만 출력(코드펜스·설명 없이)."""


def art_direction_block(style_direction: str | None) -> str:
    """사용자가 준 미감 방향을 프롬프트에 주입. 비면 모델이 자유 선택(현행)."""
    s = (style_direction or "").strip()
    if not s:
        return ""
    return (
        f"## 아트 디렉션 (사용자 요청 미감 — 이 방향으로 7장 일관 실행)\n"
        f"{s}\n"
        f"단, 이 미감 안에서도 충실성·가독성·'형태=내용'은 유지한다. "
        f"브랜드 토큰과 충돌하면 미감 방향을 우선하되 잉크 대비·가독성은 지킨다.\n\n"
    )
