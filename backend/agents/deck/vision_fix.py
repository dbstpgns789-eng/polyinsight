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
from ...core.llm_client import LLMClient

logger = logging.getLogger(__name__)

_CARD_RE = re.compile(r"data-screen-label", re.I)

VISION_FIX_SYSTEM = """당신은 방금 이 카드뉴스 덱을 저작한 디자이너다. 이제 **처음으로 자기 결과물을
눈으로 본다**. 첨부된 이미지는 당신의 HTML이 실제로 렌더된 카드들이다(순서대로 01, 02, …).

머릿속으로 상상한 레이아웃과 실제 렌더는 다르다. 지금 보이는 것을 **냉정하게** 판정하라.

[찾아야 할 결함 — 렌더를 봐야만 보이는 것들]
1. **죽은 공간**: 카드를 세로 3등분했을 때 통째로 빈 구획. (실측 1순위 결함 — 5장 중 4장에서 발생)
2. **겹침·잘림**: 텍스트가 다른 요소·카드 경계와 겹치거나 잘려 읽을 수 없는 곳.
3. **형상 불일치**: 본문이 말한 형태(삼각형·구슬·거친 표면 등)와 실제로 그려진 그림이 다른 곳.
4. **비율 거짓말**: 막대·게이지의 길이가 수치 비율과 안 맞는 곳.
5. **읽히지 않는 대비**: 배경과 글자 명도차가 부족해 뭉개지는 곳.

[수정 규칙 — 엄수]
- **결함이 없는 카드는 글자 하나도 바꾸지 마라.** 고칠 곳만 고쳐라(전면 재디자인 금지).
- 카드를 삭제하거나 추가하지 마라. **카드 수는 반드시 그대로**다.
- 수치·문구를 바꾸지 마라(레이아웃·시각 결함만 고친다). 단 겹쳐서 못 읽히는 텍스트를 줄이거나
  요소를 키워 공간을 채우는 것은 허용된다.
- 팔레트·서체·아크를 바꾸지 마라. 이 덱의 정체성은 유지한다.

출력: 수정된 **HTML 전문**만(코드펜스·설명 없이 <!DOCTYPE html> … </html>).
고칠 게 하나도 없다면 원본 HTML을 그대로 다시 출력하라."""


async def apply_vision_fix(html: str, card_pngs: list[bytes]) -> tuple[str, list[str]]:
    """렌더된 카드 PNG를 모델에게 보여주고 시각 결함을 수정. (수정된 html, warnings) 반환.

    실패·의심스러운 출력은 전부 원본으로 폴백한다(소프트 — 저작을 죽이지 않는다).
    """
    if not card_pngs:
        return html, ["비전 수정 건너뜀 — 렌더된 카드가 없습니다."]

    original_cards = len(_CARD_RE.findall(html))
    user = (
        f"위 이미지는 당신이 저작한 덱의 카드 {len(card_pngs)}장이 실제로 렌더된 모습이다.\n"
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

    changed = abs(len(fixed) - len(html))
    logger.info("vision fix 적용: %d→%d chars (%+d)", len(html), len(fixed), len(fixed) - len(html))
    if changed == 0:
        return fixed, []
    return fixed, []
