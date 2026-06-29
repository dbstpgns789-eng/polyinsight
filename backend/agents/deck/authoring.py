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

logger = logging.getLogger(__name__)

# 입력 원문 상한(컨텍스트 관리). 레퍼런스 HTML + 논문 전문이 입력에 함께 들어감.
_MAX_SOURCE_CHARS = 60000


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
) -> str:
    """논문 원문 → standalone HTML 덱. DEV_MOCK_LLM 시 레퍼런스 HTML 반환(무비용).

    style_direction: 사용자가 자연어로 준 미감 방향("지브리풍"·"학교 칠판"·"공공기관" 등).
    비우면 모델이 논문에 맞는 방향을 자유 선택(동질화 방지의 핵심 — 아트 디렉션).
    """
    if settings.DEV_MOCK_LLM:
        logger.info("deck author: DEV_MOCK_LLM → mock deck")
        return mock_deck_html(card_count)

    system = P.AUTHORING_SYSTEM.format(
        design_tokens=P.design_tokens(),
        persona=persona or P.DEFAULT_PERSONA,
    )
    user = P.AUTHORING_USER.format(
        few_shot_refs=P.few_shot_refs(settings.AUTHOR_FEWSHOT_N),
        section_map_text=raw_text[:_MAX_SOURCE_CHARS],
        title=metadata.title or "unknown",
        authors=", ".join(metadata.authors) if metadata.authors else "unknown",
        year=metadata.year or "unknown",
        card_count=card_count,
        art_direction=P.art_direction_block(style_direction),
    )
    raw = await llm_client.call(
        system_prompt=system,
        user_prompt=user,
        model=settings.LLM_MODEL_AUTHOR,
        # 7장 덱 ≈ 20K자 ≈ ~8K 토큰. 16000이면 2배 여유 + 비스트리밍 허용 범위.
        # (SDK는 max_tokens가 너무 커서 >10분 가능하면 streaming을 강제 → 그 임계 아래로.)
        # 카드 수를 크게 늘리는 premium 티어에선 streaming 지원이 필요(향후).
        max_tokens=settings.AUTHOR_MAX_TOKENS,
        temperature=0.5,
        timeout_s=settings.AUTHOR_TIMEOUT_S,
    )
    html = _strip_code_fence(raw)
    logger.info("deck authored: %d chars (model=%s)", len(html), settings.LLM_MODEL_AUTHOR)
    return html
