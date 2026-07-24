# -*- coding: utf-8 -*-
"""AI 디자이너 자연어 편집 — 지시 → 최소 편집 스펙(ops) → 결정적 적용.

정본 정의 docs/contracts/25 + 스펙 2026-07-24-ai-designer-edit-spec.md.
★구 구조(LLM이 덱 전체 HTML을 재출력)를 폐기: 느림 3~5분·회당 $0.32·180초 타임아웃·완성결과 폐기.
새 구조: LLM은 인벤토리 기반으로 ops(작음)만 뱉고, edit_ops.apply_ops가 data-eid로 적용한다.
반환에 '적용 건수'를 담아 0건이면 호출자가 무과금(스펙 §11-1).
"""
from __future__ import annotations

import logging

from ...core.config import settings
from ...core.llm_client import llm_client
from . import edit_prompts as P
from .edit_ops import apply_ops, parse_ops

logger = logging.getLogger(__name__)

# ops 출력은 작다(요소 몇 개의 스타일/텍스트). 저작용 32000 불필요 — 빠르고 싸게.
_OPS_MAX_TOKENS = 3000


async def apply_nl_patch(
    html: str, instruction: str, paper_text: str | None,
    inventory: list[dict] | None = None, target: dict | None = None,
) -> tuple[str, int, str]:
    """현재 덱 html + 지시 → (수정된 html, 적용 건수, summary).

    LLM은 인벤토리(요소 목록)만 보고 ops를 뱉고, apply_ops가 data-eid로 결정적 적용.
    JSON 파싱 실패·무적용은 graceful: (원본 html, 0, 설명) → 호출자가 무과금.
    DEV_MOCK_LLM 시 mock ops(무비용) — 적용 카운트/배관 검증.
    """
    if settings.DEV_MOCK_LLM:
        logger.info("nl_patch: DEV_MOCK_LLM → mock ops (no LLM)")
        raw = P.mock_ops(instruction, html)
    else:
        user = P.build_user_prompt(inventory or [], instruction, paper_text, target=target)
        raw = await llm_client.call(
            system_prompt=P.EDIT_SYSTEM,
            user_prompt=user,
            model=settings.LLM_MODEL_EDIT,   # 편집 전용(Sonnet)
            max_tokens=_OPS_MAX_TOKENS,      # ★작은 출력 = 수초·저렴(전체 HTML 재출력 폐기)
            temperature=0.3,
            timeout_s=settings.AUTHOR_TIMEOUT_S,
            stream=True,
        )

    summary, ops = parse_ops(raw)
    new_html, applied = apply_ops(html, ops)
    logger.info("nl_patch ops: %d개 지시 → %d건 적용 (model=%s)",
                len(ops), applied, settings.LLM_MODEL_EDIT)
    return new_html, applied, summary
