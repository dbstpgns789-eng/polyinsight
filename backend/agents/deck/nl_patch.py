# -*- coding: utf-8 -*-
"""자연어 편집(3c) — 사용자 지시로 기존 덱 HTML을 최소 변경 수정 (1회 LLM 호출).

저작(author_deck)과 분리: 백지 창작이 아니라 '기존 덱 보존 + 국소 수정'. 출력은 다시
verify_deck(V)로 사후 검증되고 render_deck로 PNG 재생성된다(pipeline.persist_edited_deck).
"""
from __future__ import annotations

import logging

from ...core.config import settings
from ...core.llm_client import llm_client
from .authoring import _strip_code_fence
from . import edit_prompts as P

logger = logging.getLogger(__name__)

# 입력 상한(컨텍스트 관리). 덱 HTML이 큼 — 원문/HTML 각각 이 상한으로 자른다.
_MAX_INPUT_CHARS = 80000


async def apply_nl_patch(
    html: str, instruction: str, paper_text: str | None, target: dict | None = None,
) -> str:
    """현재 덱 HTML + 자연어 지시 → 최소 변경 수정된 HTML 전문.

    DEV_MOCK_LLM 시 LLM 없이 마커 주석만 주입(무비용 배관 검증 — 계약/구조 보존).
    """
    if settings.DEV_MOCK_LLM:
        logger.info("nl_patch: DEV_MOCK_LLM → marker injection (no LLM)")
        marker = f"<!-- nlpatch-mock: {instruction.strip()[:80]} -->"
        if "</body>" in html:
            return html.replace("</body>", marker + "</body>", 1)
        return html + marker

    user = P.build_user_prompt(html, instruction, paper_text, html_cap=_MAX_INPUT_CHARS, target=target)
    raw = await llm_client.call(
        system_prompt=P.EDIT_SYSTEM,
        user_prompt=user,
        model=settings.LLM_MODEL_EDIT,           # 편집 전용(Sonnet) — 저작용 Opus 대비 빠름
        max_tokens=settings.AUTHOR_MAX_TOKENS,
        temperature=0.3,                         # 편집은 보수적으로(최소 변경)
        timeout_s=settings.AUTHOR_TIMEOUT_S,
        stream=True,
    )
    patched = _strip_code_fence(raw)
    logger.info("nl_patch applied: %d → %d chars (model=%s)",
                len(html), len(patched), settings.LLM_MODEL_EDIT)
    return patched
