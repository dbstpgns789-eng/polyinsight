# -*- coding: utf-8 -*-
"""S6 단일 저작(Deck Authoring) — 한 번의 LLM 호출로 standalone HTML 덱을 저작 (헌법 v3.0).

architect/writer 분리·30 카탈로그 선택·필드 스키마 없음. 강한 모델이 [논문+토큰+레퍼런스]를
받아 스토리·형태·표현을 한 번에 빚는다. 충실성은 코드(V, fidelity.verify_deck)가 사후 검증.
"""
from __future__ import annotations

import logging

from ...core.config import settings
from ...core.llm_client import llm_client
from ...core.models import PaperMetadata
from . import authoring_prompts as P
from .mock import mock_deck_html
from .source_trim import trim_source

logger = logging.getLogger(__name__)

# 입력 원문 상한 — **자르지 않는 것이 기본**이다.
#
# 원래 60,000이었다. 왜 60,000인지 아무도 묻지 않았고, 그 때문에 chitosan(81,518자)의
# **결론이 175자 차이로 잘렸다**. 그래서 참고문헌을 걷어냈다(source_trim). 거기서 멈추면 안 됐다 —
# **상한 자체를 의심했어야 했다.**
#
# 실측:
#   Opus 4.8 컨텍스트 = 200,000 토큰
#   논문 1자 ≈ 0.636 토큰 (PDF 추출 텍스트)
#   20만 자(60p 리뷰논문)도 총 입력 135,034 토큰 = 컨텍스트의 68%. **여유가 있다.**
#   7만 자 → 20만 자로 늘려도 입력 비용은 +$0.45.
#
# 그 $0.45를 아끼려고 **Methods의 실험 조건**(12.5kV·0.32wt% — 우리 카드가 실제로 쓰는 수치)을
# 버리고 있었다. 논문을 자르는 건 정보를 버리는 것이고, 그 대가가 $0.45라면 자르지 않는 게 맞다.
#
# 180,000자 = 총 입력 ~122,000 토큰(컨텍스트 61%). 사실상 모든 논문이 통째로 들어간다.
# 이 위(학위논문·단행본)에서만 중간 생략이 발동한다 — 그때도 결론은 보존한다.
MAX_SOURCE_CHARS = 180000


def _strip_code_fence(text: str) -> str:
    """모델이 ```html … ``` 로 감싸 출력해도 HTML 본문만 남긴다."""
    t = text.strip()
    if t.startswith("```"):
        nl = t.find("\n")
        if nl != -1:
            t = t[nl + 1:]
        end = t.rfind("```")
        if end != -1:
            t = t[:end]
    return t.strip()


async def author_deck(
    *,
    raw_text: str,
    metadata: PaperMetadata,
    card_count: int,
    persona: str | None = None,
    style_direction: str | None = None,
    publisher: str | None = None,
    history_block: str = "",
    figures: list[bytes] | None = None,
) -> str:
    """논문 원문 → standalone HTML 덱. DEV_MOCK_LLM 시 레퍼런스 HTML 반환(무비용).

    style_direction: 사용자가 자연어로 준 미감 방향("지브리풍"·"학교 칠판"·"공공기관" 등).
    비우면 모델이 논문에 맞는 방향을 자유 선택(동질화 방지의 핵심 — 아트 디렉션).
    publisher: 발행 주체(기관명·핸들). 유저가 주면 그대로, 비우면 모델이 논문 본문 소속에서 읽어 채운다.
    history_block: 이 계정의 최근 덱 매니페스트(아크·팔레트·모티프) — 소프트 변주 선호.
    모델은 자기가 지난주에 뭘 만들었는지 모른다. 다양성은 파이프라인만 가진 정보(이력)에서 나온다.
    figures: 이 논문의 그림(SEM·그래프·도식) PNG — '논문이 곧 레퍼런스'(D안).
    남의 덱(refs)이 아니라 논문 자신을 시각 앵커로 준다. 논문마다 그림이 다르므로 동질화가 불가능.
    """
    if settings.DEV_MOCK_LLM:
        logger.info("deck author: DEV_MOCK_LLM → mock deck")
        return mock_deck_html(card_count)

    system = P.AUTHORING_SYSTEM.format(
        persona=persona or P.DEFAULT_PERSONA,
    )
    # 참고문헌을 걷어내고, 그래도 길면 **중간을 생략**한다(앞에서 자르면 결론부터 버린다).
    source, _ = trim_source(raw_text, MAX_SOURCE_CHARS)
    user = P.AUTHORING_USER.format(
        few_shot_refs=P.few_shot_refs(settings.AUTHOR_FEWSHOT_N),
        section_map_text=source,
        title=metadata.title or "unknown",
        authors=", ".join(metadata.authors) if metadata.authors else "unknown",
        year=metadata.year or "unknown",
        card_count=card_count,
        art_direction=P.art_direction_block(style_direction),
        publisher=publisher or "(미지정 — 논문 본문 소속에서 읽어 채워라)",
        history_block=history_block,
        figure_block=P.figure_block(len(figures or [])),
    )
    raw = await llm_client.call(
        system_prompt=system,
        user_prompt=user,
        model=settings.LLM_MODEL_AUTHOR,
        max_tokens=settings.AUTHOR_MAX_TOKENS,  # 32000 — 정교한 스타일도 안 잘림
        temperature=0.5,
        timeout_s=settings.AUTHOR_TIMEOUT_S,
        stream=True,                            # 대용량 출력 → streaming(>10분 제한 무관)
        images=figures or None,                 # 논문의 그림을 모델이 직접 본다
    )
    html = _strip_code_fence(raw)
    logger.info("deck authored: %d chars (model=%s)", len(html), settings.LLM_MODEL_AUTHOR)
    return html
