"""콘텐츠팀 Writer — 확정된 Storyboard를 받아 각 카드 fields를 채운다. (Haiku)

레이아웃은 이미 정해졌다. Writer는 fields만 grounded·재작성으로 채우고,
뼈대에 내용이 안 맞으면 mismatch_signals로 설계팀에 되돌린다.
"""
from __future__ import annotations

import json
import logging

from ...core.llm_client import llm_client
from ...core.models import (
    CardMeta, CardSlot, FieldValue, MismatchSignal, Storyboard,
    WriterInput, WriterOutput,
)
from ._util import extract_json, format_section_map
from . import prompts

logger = logging.getLogger(__name__)


class Writer:
    """WriterInput → WriterOutput. 코디네이터가 호출한다."""

    async def run(self, inp: WriterInput) -> WriterOutput:
        meta = inp.paper_metadata
        only = set(inp.only_beats or [])
        user = prompts.WRITER_USER.format(
            section_map_text=format_section_map(inp.section_map),
            title=meta.title or "unknown",
            authors=", ".join(meta.authors) if meta.authors else "unknown",
            year=meta.year or "unknown",
            org=", ".join(meta.authors[:1]) if meta.authors else "unknown",
            storyboard_text=_storyboard_text(inp.storyboard, only),
            template_spec=prompts.TEMPLATE_SPEC,
            only_beats_note=_only_note(only),
        )

        raw = await llm_client.call(
            system_prompt=prompts.WRITER_SYSTEM,
            user_prompt=user,
            max_tokens=16000,
            temperature=0.2,
            timeout_s=120,
        )
        parsed = json.loads(extract_json(raw))

        beat_types = {b.card_num: b.template_type for b in inp.storyboard.beats}
        cards: list[CardSlot] = []
        for raw_card in parsed.get("cards", []):
            card_num = raw_card["card_num"]
            if only and card_num not in only:
                continue                                  # 부분 재작성: 대상만
            fields = {k: FieldValue.model_validate(v) for k, v in raw_card.get("fields", {}).items()}
            # 스토리보드가 진실 — 모델이 template_type을 어기면 교정.
            tt = beat_types.get(card_num, raw_card["template_type"])
            cards.append(CardSlot(card_num=card_num, template_type=tt, fields=fields))

        meta_out = CardMeta.model_validate(parsed["meta"])
        signals = [MismatchSignal.model_validate(s) for s in parsed.get("mismatch_signals", [])]
        if only:
            signals = [s for s in signals if s.card_num in only]
        return WriterOutput(cards=cards, meta=meta_out, mismatch_signals=signals)


def _storyboard_text(sb: Storyboard, only: set[int]) -> str:
    lines = []
    for b in sb.beats:
        mark = "   ← 이번에 작성" if (only and b.card_num in only) else ""
        lines.append(
            f"- 카드{b.card_num} [{b.template_type}] 역할:{b.narrative_role} | 핵심:{b.key_message}{mark}"
        )
    return "\n".join(lines)


def _only_note(only: set[int]) -> str:
    if only:
        nums = ", ".join(str(n) for n in sorted(only))
        return f"★이번엔 카드 {nums} 만 다시 작성하라. 나머지 카드는 출력하지 마라."
    return "스토리보드의 모든 비트를 작성하라."


writer = Writer()
