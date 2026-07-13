# -*- coding: utf-8 -*-
"""비전 자기수정 — 모델이 자기 카드의 **렌더 결과**를 보고 고친다 (2026-07-13).

왜 이것이 유일한 남은 레버인가:
  실측(after-0712, 5편)에서 모델은 PI_SELFCHECK에 **5편 전부 "전항 통과"**라 자가신고했는데,
  저지는 5편 전부에서 결함을 찾았다(dead_zone 4/5). 모델은 자기가 쓴 HTML이 어떻게 렌더되는지
  **볼 수 없다**. 빈 공간·요소 겹침·형상 오독은 텍스트 체크리스트로는 원리적으로 안 잡힌다.
  프롬프트 백 줄보다 스크린샷 한 장이 빠르다.

설계 결정:
  - **전체 HTML 재출력**(국소 패치 아님). 카드 div 경계를 정규식으로 오려붙이는 건 중첩 div에서
    깨진다 — 단순함이 안전함이다. 대신 "결함 없는 카드는 글자 하나 바꾸지 마라"를 강제한다.
  - **가드레일**: 카드 수가 줄거나 카드가 사라지면 **수정을 버리고 원본을 쓴다**.
    멀쩡한 덱을 수정이 망가뜨리는 게 최악이다.
  - 실패는 전부 **소프트** — 저작(비싼 것)을 수정 단계가 죽이면 안 된다.
"""
from __future__ import annotations

import logging
import re

from ...core.config import settings
from ...core.fidelity import verify_deck
from ...core.llm_client import LLMClient

logger = logging.getLogger(__name__)

_CARD_RE = re.compile(r"data-screen-label", re.I)


def _quant_set(html: str) -> set[str]:
    """덱에 실린 정량 수치 집합. fidelity의 검증된 추출기를 재사용(중복 구현 금지).

    verify_deck은 (수치, 원문존재여부)를 내는데 여기선 수치 토큰만 쓴다 —
    paper_text를 빈 문자열로 줘도 추출 자체는 동일하다.
    """
    return {c.value for c in verify_deck(html, "")}

VISION_FIX_SYSTEM = """당신은 방금 이 카드뉴스 덱을 저작한 디자이너다. 이제 **처음으로 자기 결과물을
눈으로 본다**. 첨부된 이미지는 당신의 HTML이 실제로 렌더된 카드들이다(순서대로 01, 02, …).

머릿속으로 상상한 레이아웃과 실제 렌더는 다르다. 지금 보이는 것을 **냉정하게** 판정하라.

[찾아야 할 결함 — 렌더를 봐야만 보이는 것들]
1. **죽은 공간**: 카드를 세로 3등분했을 때 통째로 빈 구획. (실측 1순위 결함 — 5장 중 4장에서 발생)
2. **겹침·잘림**: 텍스트가 다른 요소·카드 경계와 겹치거나 잘려 읽을 수 없는 곳.
3. **형상 불일치**: 본문이 말한 형태(삼각형·구슬·거친 표면 등)와 실제로 그려진 그림이 다른 곳.
4. **비율 거짓말**: 막대·게이지의 길이가 수치 비율과 안 맞는 곳. **눈으로 길이를 재라** —
   값이 8배인데 막대가 2배로 보이면 거짓말이다. 값의 스케일 차가 100배를 넘어 선형 막대로는
   작은 값이 보이지도 않는다면, 막대를 버리고 다른 형태(수치 나열·로그 축 명시·계단)로 바꿔라.
5. **읽히지 않는 대비**: 배경과 글자 명도차가 부족해 뭉개지는 곳.
6. **외계어**: 카드에 적힌 글자를 **비전공자의 눈으로 읽어라**. 앵커(쉬운 말·비유) 없이 등장한
   전문용어·단위·약어가 있는가? (실측 결함: 'nm', 'wt%', '아민기·수산기·수소결합', 'SGD', 'O(n)')
   있으면 그 자리에서 짧은 앵커를 붙여라('약 100나노미터 — 머리카락 굵기의 천분의 일').
   앵커를 붙일 공간이 없으면 그 용어를 **쉬운 말로 갈아치워라**. 논문 용어를 지키는 것보다
   독자가 이해하는 게 우선이다(단, 수치 자체는 절대 바꾸지 마라).

[수정 규칙 — 엄수]
- **결함이 없는 카드는 글자 하나도 바꾸지 마라.** 고칠 곳만 고쳐라(전면 재디자인 금지).
- 카드를 삭제하거나 추가하지 마라. **카드 수는 반드시 그대로**다.
- ★**수치는 절대 바꾸지 마라.** 숫자·단위·비율은 원문에서 온 것이다. 건드리면 충실성이 깨진다.
  (용어를 쉽게 풀거나 앵커를 붙이는 것은 허용 — 수치를 손대는 것과는 다르다.)
- 팔레트·서체·아크를 바꾸지 마라. 이 덱의 정체성은 유지한다.
- ★★**당신의 수정이 새 결함을 만든다** (실측: 용어 앵커를 넣어 텍스트가 길어지자 제목과 수치가
  겹쳤다 — finish 4→1). 텍스트를 **늘리는** 수정을 할 때는 그 카드의 다른 요소가 밀려나지 않는지
  세로 픽셀을 다시 합산하라. 공간이 없으면 **길게 덧붙이지 말고 다른 말을 줄여라**.
  고치는 것보다 **망가뜨리지 않는 것**이 우선이다.

출력: 수정된 **HTML 전문**만(코드펜스·설명 없이 <!DOCTYPE html> … </html>).
고칠 게 하나도 없다면 원본 HTML을 그대로 다시 출력하라."""


async def apply_vision_fix(
    html: str,
    card_pngs: list[bytes],
    *,
    round_no: int = 1,
) -> tuple[str, list[str]]:
    """렌더된 카드 PNG를 모델에게 보여주고 시각 결함을 수정. (수정된 html, warnings) 반환.

    실패·의심스러운 출력은 전부 원본으로 폴백한다(소프트 — 저작을 죽이지 않는다).
    round_no≥2면 '당신의 이전 수정 결과'임을 알려준다(수정이 만든 새 결함을 잡기 위해).
    """
    if not card_pngs:
        return html, ["비전 수정 건너뜀 — 렌더된 카드가 없습니다."]

    original_cards = len(_CARD_RE.findall(html))
    if round_no == 1:
        lead = f"위 이미지는 당신이 저작한 덱의 카드 {len(card_pngs)}장이 실제로 렌더된 모습이다."
    else:
        lead = (
            f"위 이미지는 **당신이 방금 수정한 결과**가 다시 렌더된 모습이다({len(card_pngs)}장).\n"
            "수정이 새 결함을 만들었을 수 있다(텍스트를 늘려 다른 요소를 밀어냈다든지).\n"
            "**남은 결함이 없다면 HTML을 그대로 다시 출력하라** — 억지로 더 고치지 마라."
        )
    user = (
        f"{lead}\n"
        "아래는 그 HTML이다. 위 결함 목록으로 카드를 하나씩 검사하고, **발견한 결함만** 고쳐라.\n\n"
        f"```\n{html}\n```"
    )

    try:
        client = LLMClient()   # 호출당 생성(이벤트 루프 안전)
        raw = await client.call(
            system_prompt=VISION_FIX_SYSTEM,
            user_prompt=user,
            model=settings.LLM_MODEL_AUTHOR,
            max_tokens=settings.AUTHOR_MAX_TOKENS,
            timeout_s=settings.AUTHOR_TIMEOUT_S,
            stream=True,
            images=card_pngs,
        )
    except Exception as exc:
        logger.warning("vision fix 실패(%s) — 원본 유지", exc)
        return html, [f"비전 수정 실패 — 원본을 유지합니다 ({type(exc).__name__})."]

    fixed = raw.strip()
    if fixed.startswith("```"):                       # 코드펜스 제거
        nl = fixed.find("\n")
        fixed = fixed[nl + 1:] if nl != -1 else fixed
        end = fixed.rfind("```")
        if end != -1:
            fixed = fixed[:end]
        fixed = fixed.strip()

    if "data-screen-label" not in fixed:
        logger.warning("vision fix: 카드 없는 출력 — 무시")
        return html, ["비전 수정 출력에 카드가 없어 무시했습니다 — 원본을 유지합니다."]

    fixed_cards = len(_CARD_RE.findall(fixed))
    if fixed_cards < original_cards:                  # 카드를 삼키는 사고 차단
        logger.warning("vision fix: 카드 수 감소 %d→%d — 무시", original_cards, fixed_cards)
        return html, [
            f"비전 수정이 카드 수를 줄여({original_cards}→{fixed_cards}) 무시했습니다 — 원본을 유지합니다."
        ]

    # ★수치 불변 가드 — 비전 수정은 레이아웃·표현을 고치는 단계이지 사실을 바꾸는 단계가 아니다.
    # 프롬프트로 "수치를 바꾸지 마라"고 말했지만, 말은 지켜지지 않을 수 있다(실측: L4 자가검수는
    # 5/5 무력했다). 코드가 확인한다 — 정량 수치 집합이 줄어들면 수정을 버린다.
    before_nums = _quant_set(html)
    after_nums = _quant_set(fixed)
    lost = before_nums - after_nums
    if lost:
        logger.warning("vision fix: 수치 소실 %s — 무시", sorted(lost)[:5])
        return html, [
            f"비전 수정이 수치를 변경/삭제해({', '.join(sorted(lost)[:3])}) 무시했습니다 — 원본을 유지합니다."
        ]

    logger.info("vision fix 적용: %d→%d chars (%+d)", len(html), len(fixed), len(fixed) - len(html))
    return fixed, []
